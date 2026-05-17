#!/usr/bin/env python3
"""Run prompts/discovery.md against interval JSONL rows with `codex exec`.

Each input JSONL line is loaded as an interval record. The script replaces
`{candidate_row}` and `{interval_index}` in the prompt template, then invokes
Codex non-interactively. Each run asks Codex to write:

    candidates/candidate_<interval_index>.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INTERVAL_MINUTES = 15
DEFAULT_TEMPLATE = REPO_ROOT / "prompts" / "discovery.md"
DEFAULT_CANDIDATES_DIR = REPO_ROOT / "candidates"


def default_intervals_path(interval_minutes: int) -> Path:
    return REPO_ROOT / "data" / f"log_intervals_{interval_minutes}m.jsonl"


def default_candidates_dir(interval_minutes: int, interval_minutes_was_given: bool) -> Path:
    if not interval_minutes_was_given and interval_minutes == DEFAULT_INTERVAL_MINUTES:
        return DEFAULT_CANDIDATES_DIR
    return REPO_ROOT / f"candidates_{interval_minutes}m"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSON in {path}:{line_num}: {exc}") from exc
            if not isinstance(row, dict):
                raise SystemExit(f"expected object in {path}:{line_num}")
            row.setdefault("interval_index", line_num - 1)
            rows.append(row)
    return rows


def render_prompt(template: str, row: dict[str, Any], candidate_path: Path) -> str:
    interval_index = row.get("interval_index")
    if interval_index is None:
        raise SystemExit(f"row is missing interval_index: {row}")

    candidate_row = json.dumps(row, ensure_ascii=False, sort_keys=True)
    rendered = (
        template.replace("{candidate_row}", candidate_row)
        .replace("{interval_index}", str(interval_index))
    )
    return (
        rendered
        + "\n\n"
        + "For this codex-exec run, write the JSON file to this exact path: "
        + str(candidate_path)
        + "\n"
    )


def parse_interval_indexes(raw: str | None) -> set[int] | None:
    if not raw:
        return None

    indexes: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_raw, end_raw = part.split("-", 1)
            start = int(start_raw)
            end = int(end_raw)
            if end < start:
                raise SystemExit(f"invalid interval range: {part}")
            indexes.update(range(start, end + 1))
        else:
            indexes.add(int(part))
    return indexes


def append_run_log(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        f.write("\n")


def build_codex_command(args: argparse.Namespace) -> list[str]:
    command = [
        args.codex_bin,
        "exec",
        "-m",
        args.model,
        "-c",
        f'model_reasoning_effort="{args.reasoning_effort}"',
        "--sandbox",
        args.sandbox,
        "--cd",
        str(args.repo_root),
    ]

    if args.ephemeral:
        command.append("--ephemeral")
    if args.ignore_user_config:
        command.append("--ignore-user-config")
    if args.ignore_rules:
        command.append("--ignore-rules")
    if args.json_events:
        command.append("--json")

    command.append("-")
    return command


def stream_pipe(pipe, log_file, console, prefix: str) -> None:
    try:
        for line in iter(pipe.readline, ""):
            log_file.write(line)
            log_file.flush()
            console.write(f"{prefix}{line}")
            console.flush()
    finally:
        pipe.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interval-minutes",
        type=int,
        help=(
            "Interval size used to derive default paths. For example, 30 uses "
            "data/log_intervals_30m.jsonl and candidates_30m/."
        ),
    )
    parser.add_argument(
        "--intervals",
        type=Path,
        help="Input JSONL of interval rows. Defaults to data/log_intervals_<minutes>m.jsonl.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="Prompt template containing {candidate_row} and {interval_index}.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Working repository passed to `codex exec --cd`.",
    )
    parser.add_argument(
        "--candidates-dir",
        type=Path,
        help="Directory where candidate_<interval_index>.json files are expected.",
    )
    parser.add_argument(
        "--run-log",
        type=Path,
        help="JSONL run ledger written by this wrapper. Defaults inside --candidates-dir.",
    )
    parser.add_argument(
        "--interval-indexes",
        help="Comma-separated interval indexes or ranges to run, e.g. `0,3,10-12`.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start offset within the filtered row list.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of filtered rows to run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if candidates/candidate_<interval_index>.json already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the command and rendered prompt previews without invoking Codex.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="With --dry-run, print full rendered prompts instead of previews.",
    )
    parser.add_argument("--codex-bin", default="codex", help="Codex executable.")
    parser.add_argument("--model", default="gpt-5.5", help="Model passed with -m.")
    parser.add_argument(
        "--reasoning-effort",
        default="xhigh",
        help="Reasoning effort passed with `-c reasoning_effort=...`.",
    )
    parser.add_argument(
        "--sandbox",
        default="workspace-write",
        choices=("read-only", "workspace-write", "danger-full-access"),
        help="Sandbox mode for Codex-generated commands.",
    )
    parser.add_argument(
        "--ephemeral",
        action="store_true",
        help="Pass --ephemeral to codex exec.",
    )
    parser.add_argument(
        "--ignore-user-config",
        action="store_true",
        help="Pass --ignore-user-config to codex exec.",
    )
    parser.add_argument(
        "--ignore-rules",
        action="store_true",
        help="Pass --ignore-rules to codex exec.",
    )
    parser.add_argument(
        "--json-events",
        action="store_true",
        help="Pass --json to codex exec and store JSONL events in stdout log files.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue to later intervals if one codex exec run fails.",
    )
    args = parser.parse_args()

    interval_minutes_was_given = args.interval_minutes is not None
    interval_minutes = args.interval_minutes or DEFAULT_INTERVAL_MINUTES
    if interval_minutes <= 0:
        raise SystemExit("--interval-minutes must be greater than 0")

    if args.intervals is None:
        args.intervals = default_intervals_path(interval_minutes)
    if args.candidates_dir is None:
        args.candidates_dir = default_candidates_dir(
            interval_minutes, interval_minutes_was_given
        )
    if args.run_log is None:
        args.run_log = args.candidates_dir / "codex_exec_runs.jsonl"

    args.repo_root = args.repo_root.resolve()
    args.intervals = args.intervals.resolve()
    args.template = args.template.resolve()
    args.candidates_dir = args.candidates_dir.resolve()
    args.run_log = args.run_log.resolve()

    if not args.intervals.exists():
        raise SystemExit(f"interval JSONL not found: {args.intervals}")
    if not args.template.exists():
        raise SystemExit(f"prompt template not found: {args.template}")
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")

    template = args.template.read_text(encoding="utf-8")
    if "{candidate_row}" not in template:
        raise SystemExit(f"template missing {{candidate_row}} placeholder: {args.template}")

    selected_indexes = parse_interval_indexes(args.interval_indexes)
    rows = read_jsonl(args.intervals)
    if selected_indexes is not None:
        rows = [row for row in rows if int(row["interval_index"]) in selected_indexes]

    rows = rows[args.start :]
    if args.limit is not None:
        rows = rows[: args.limit]

    if not rows:
        print("no rows selected", file=sys.stderr)
        return 0

    args.candidates_dir.mkdir(parents=True, exist_ok=True)
    command = build_codex_command(args)
    print(f"selected rows: {len(rows)}", file=sys.stderr)
    print("codex command:", " ".join(command), file=sys.stderr)

    failures = 0
    for row in rows:
        interval_index = int(row["interval_index"])
        candidate_path = args.candidates_dir / f"candidate_{interval_index}.json"
        if candidate_path.exists() and not args.force:
            print(f"skip interval {interval_index}: {candidate_path} exists", file=sys.stderr)
            continue

        prompt = render_prompt(template, row, candidate_path)
        if args.dry_run:
            print(f"\n--- interval {interval_index} ---")
            print(f"candidate path: {candidate_path}")
            if args.print_prompt:
                print(prompt)
            else:
                print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
            continue

        started_at = datetime.now(timezone.utc).isoformat()
        print(f"run interval {interval_index} -> {candidate_path}", file=sys.stderr)
        stdout_path = args.candidates_dir / f"candidate_{interval_index}.stdout.log"
        stderr_path = args.candidates_dir / f"candidate_{interval_index}.stderr.log"
        with stdout_path.open("w", encoding="utf-8") as stdout_log, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_log:
            proc = subprocess.Popen(
                command,
                cwd=args.repo_root,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            assert proc.stdin is not None
            assert proc.stdout is not None
            assert proc.stderr is not None

            stdout_thread = threading.Thread(
                target=stream_pipe,
                args=(proc.stdout, stdout_log, sys.stdout, f"[{interval_index} stdout] "),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=stream_pipe,
                args=(proc.stderr, stderr_log, sys.stderr, f"[{interval_index} stderr] "),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            proc.stdin.write(prompt)
            proc.stdin.close()
            returncode = proc.wait()
            stdout_thread.join()
            stderr_thread.join()
        completed_at = datetime.now(timezone.utc).isoformat()

        record = {
            "interval_index": interval_index,
            "candidate_path": str(candidate_path),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "returncode": returncode,
            "started_at": started_at,
            "completed_at": completed_at,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "sandbox": args.sandbox,
        }
        append_run_log(args.run_log, record)

        if returncode != 0:
            failures += 1
            print(
                f"interval {interval_index} failed with exit code {returncode}; "
                f"see {stderr_path}",
                file=sys.stderr,
            )
            if not args.continue_on_error:
                return returncode

        if not candidate_path.exists():
            failures += 1
            print(
                f"interval {interval_index} completed but did not create {candidate_path}",
                file=sys.stderr,
            )
            if not args.continue_on_error:
                return 1

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
