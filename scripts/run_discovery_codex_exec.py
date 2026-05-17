#!/usr/bin/env python3
"""Run discovery.md against interval JSONL rows with `codex exec`.

Each input JSONL line is loaded as an interval record. The script replaces
`{candidate_row}` and `{interval_index}` in the prompt template, then invokes
Codex non-interactively. By default, each run asks Codex to write:

    candidates/candidate_<interval_index>.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INTERVALS = REPO_ROOT / "data" / "log_intervals_15m.jsonl"
DEFAULT_TEMPLATE = REPO_ROOT / "discovery.md"
DEFAULT_CANDIDATES_DIR = REPO_ROOT / "candidates"
DEFAULT_RUN_LOG = REPO_ROOT / "candidates" / "codex_exec_runs.jsonl"


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
        f'reasoning_effort="{args.reasoning_effort}"',
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--intervals",
        type=Path,
        default=DEFAULT_INTERVALS,
        help="Input JSONL of interval rows.",
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
        default=DEFAULT_CANDIDATES_DIR,
        help="Directory where candidate_<interval_index>.json files are expected.",
    )
    parser.add_argument(
        "--run-log",
        type=Path,
        default=DEFAULT_RUN_LOG,
        help="JSONL run ledger written by this wrapper.",
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
        proc = subprocess.run(
            command,
            cwd=args.repo_root,
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        completed_at = datetime.now(timezone.utc).isoformat()

        stdout_path = args.candidates_dir / f"candidate_{interval_index}.stdout.log"
        stderr_path = args.candidates_dir / f"candidate_{interval_index}.stderr.log"
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")

        record = {
            "interval_index": interval_index,
            "candidate_path": str(candidate_path),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "returncode": proc.returncode,
            "started_at": started_at,
            "completed_at": completed_at,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "sandbox": args.sandbox,
        }
        append_run_log(args.run_log, record)

        if proc.returncode != 0:
            failures += 1
            print(
                f"interval {interval_index} failed with exit code {proc.returncode}; "
                f"see {stderr_path}",
                file=sys.stderr,
            )
            if not args.continue_on_error:
                return proc.returncode

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
