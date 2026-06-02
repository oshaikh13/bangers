from __future__ import annotations

import argparse
import json
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_job import agent_log_paths, cleanup_isolated_workdir, run_agent_job
from .cli import add_claude_args, add_codex_args
from .intervals import select_rows
from .io import append_jsonl, read_jsonl
from .paths import (
    DEFAULT_GENERIC_QA_COMMON_TEMPLATE,
    DEFAULT_GENERIC_QA_PROMPTS_DIR,
    DEFAULT_INTERVAL_MINUTES,
    REPO_ROOT,
    default_discovery_dir,
    default_intervals_path,
)
from .prompts import load_template, render_generic_qa_prompt
from .providers import build_provider_command
from .qa_validation import valid_context_indexes, validate_grounded_pair
from .question_context import (
    QUESTION_CONTEXT_EVENT_COUNT,
    context_events_for_timestamp,
    load_indexed_events,
    parse_timestamp,
)
from .runner import (
    create_isolated_workdir,
    write_json_atomically,
)
from .scoping import scoped_stage_dir, scope_slug, selector_slug


QA_TYPES = (
    "activity_window",
    "todo",
    "predictive_actions",
    "verbatim_textbox",
    "predictive_struggles",
    "assistant_utility",
    "affective_state",
    "cognitive_state",
    "dropped_commitments",
    "identity",
    "hypothetical",
    "recall",
    "current_state",
)

SPARSE_QA_TYPES = frozenset({"verbatim_textbox"})

MIN_QAS_PER_INTERVAL = 2
MAX_QAS_PER_INTERVAL = 5
DEFAULT_QAS_PER_INTERVAL = 2


@dataclass(frozen=True)
class GenericQAResult:
    qa_type: str
    interval_index: int
    record: dict[str, Any]
    qa_path: Path
    stderr_path: Path
    returncode: int
    created_qa: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run pipeline 10: one-stage generic QA generation with one QA type "
            "per model call."
        )
    )
    parser.add_argument(
        "--provider",
        choices=("codex", "claude"),
        default="codex",
        help="Agent CLI used for each generic QA run.",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        help="Interval size used to derive default paths.",
    )
    parser.add_argument(
        "--intervals",
        type=Path,
        help="Input JSONL of interval rows. Defaults to data/log_intervals_<minutes>m.jsonl.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Working repository passed to the agent CLI.",
    )
    parser.add_argument(
        "--discovery-dir",
        help="Discovery run directory. Defaults to discovery_<provider>_<minutes>m.",
    )
    parser.add_argument(
        "--generic-qa-dir",
        help=(
            "Pipeline 10 output directory. Defaults to scoped "
            "<discovery-dir>/10_generic_qa."
        ),
    )
    parser.add_argument(
        "--run-log",
        help="JSONL run ledger. Defaults inside --discovery-dir.",
    )
    parser.add_argument(
        "--common-template",
        default=str(DEFAULT_GENERIC_QA_COMMON_TEMPLATE),
        help="Shared prompt template for pipeline 10.",
    )
    parser.add_argument(
        "--prompts-dir",
        default=str(DEFAULT_GENERIC_QA_PROMPTS_DIR),
        help="Directory containing prompts/10_generic_qa_<qa_type>.md files.",
    )
    parser.add_argument(
        "--qa-types",
        default="all",
        help=(
            "Comma-separated QA types to run, or 'all'. Known types: "
            + ", ".join(QA_TYPES)
        ),
    )
    parser.add_argument(
        "--pairs-per-run",
        type=int,
        default=DEFAULT_QAS_PER_INTERVAL,
        help="Number of Q/A pairs requested for each interval. Defaults to 2.",
    )
    parser.add_argument(
        "--interval-indexes",
        help="Comma-separated interval indexes or ranges to run, e.g. `0,3,10-12`.",
    )
    parser.add_argument(
        "--days",
        "--day",
        dest="days",
        help=(
            "Comma-separated zero-based day numbers or ranges to run, e.g. "
            "`0` or `0-4`. Days are derived from interval row start dates."
        ),
    )
    parser.add_argument("--start", type=int, default=0, help="Start offset.")
    parser.add_argument("--limit", type=int, help="Maximum number of interval rows to run.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if the expected qa_<interval_index>.json output exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands and prompt previews without invoking the agent CLI.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="With --dry-run, print full rendered prompts instead of previews.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue to later selected items if one agent run fails.",
    )
    parser.add_argument("--jobs", type=int, default=1, help="Concurrent model calls.")
    parser.add_argument(
        "--no-isolate-agent-workdir",
        action="store_true",
        help=(
            "Run the agent in the real repo. By default each run uses a "
            "temporary workdir with logs-indexed and agent-output."
        ),
    )
    parser.add_argument(
        "--keep-agent-workdirs",
        action="store_true",
        help="Do not delete temporary isolated workdirs after each run.",
    )
    parser.add_argument(
        "--screenshot-link-mode",
        choices=("hardlink", "symlink"),
        default="hardlink",
        help="How isolated workdirs expose logs-indexed/screenshots.",
    )
    parser.add_argument(
        "--startup-progress-every",
        type=int,
        default=5000,
        help="Minimum screenshot files between startup progress refreshes.",
    )
    add_codex_args(parser)
    add_claude_args(parser)
    return parser


def parse_qa_types(raw: str) -> list[str]:
    if raw.strip() == "all":
        return list(QA_TYPES)

    parsed = [part.strip() for part in raw.split(",") if part.strip()]
    if not parsed:
        raise SystemExit("--qa-types must not be empty")

    unknown = [qa_type for qa_type in parsed if qa_type not in QA_TYPES]
    if unknown:
        known = ", ".join(QA_TYPES)
        raise SystemExit(f"unknown QA type(s): {', '.join(unknown)}; known: {known}")

    deduped: list[str] = []
    seen: set[str] = set()
    for qa_type in parsed:
        if qa_type in seen:
            continue
        seen.add(qa_type)
        deduped.append(qa_type)
    return deduped


def normalize_args(args: argparse.Namespace) -> None:
    interval_minutes = args.interval_minutes or DEFAULT_INTERVAL_MINUTES
    if interval_minutes <= 0:
        raise SystemExit("--interval-minutes must be greater than 0")
    if args.jobs <= 0:
        raise SystemExit("--jobs must be greater than 0")
    if args.pairs_per_run <= 0:
        raise SystemExit("--pairs-per-run must be greater than 0")
    if args.pairs_per_run > MAX_QAS_PER_INTERVAL:
        raise SystemExit(f"--pairs-per-run must be at most {MAX_QAS_PER_INTERVAL}")
    if args.startup_progress_every < 0:
        raise SystemExit("--startup-progress-every must be non-negative")

    args.repo_root = Path(args.repo_root).resolve()
    args.intervals = (
        Path(args.intervals) if args.intervals is not None else default_intervals_path(interval_minutes)
    ).resolve()
    args.discovery_dir = (
        Path(args.discovery_dir)
        if args.discovery_dir
        else default_discovery_dir(args.provider, interval_minutes)
    ).resolve()
    args.scope_slug = scope_slug(args)
    args.generic_qa_dir = (
        Path(args.generic_qa_dir)
        if args.generic_qa_dir
        else scoped_stage_dir(args.discovery_dir, "10_generic_qa", args.scope_slug)
    ).resolve()
    args.run_log = (
        Path(args.run_log)
        if args.run_log
        else args.discovery_dir / f"{args.provider}_exec_runs.jsonl"
    ).resolve()
    args.common_template = Path(args.common_template).resolve()
    args.prompts_dir = Path(args.prompts_dir).resolve()
    args.qa_types = parse_qa_types(args.qa_types)

    if args.claude_stream:
        args.claude_output_format = "stream-json"
        args.claude_verbose = True
        args.claude_include_partial_messages = True
    if args.claude_include_partial_messages and args.claude_output_format != "stream-json":
        raise SystemExit("--claude-include-partial-messages requires --claude-output-format stream-json")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    args = build_parser().parse_args(argv)
    normalize_args(args)
    return args


def qa_type_template_path(args: argparse.Namespace, qa_type: str) -> Path:
    return args.prompts_dir / f"10_generic_qa_{qa_type}.md"


def load_generic_qa_template(args: argparse.Namespace, qa_type: str) -> str:
    common = load_template(
        args.common_template,
        (
            "{qa_type}",
            "{qa_timestamp}",
            "{qa_timestamp_ts}",
            "{interval_json}",
            "{context_events_json}",
            "{pairs_per_run}",
        ),
    )
    body_path = qa_type_template_path(args, qa_type)
    if not body_path.exists():
        raise SystemExit(f"QA type prompt not found: {body_path}")
    return common + "\n\n" + body_path.read_text(encoding="utf-8")


def qa_path(args: argparse.Namespace, qa_type: str, interval_index: int) -> Path:
    return args.generic_qa_dir / qa_type / f"qa_{interval_index}.json"


def agent_qa_path(agent_workdir: Path, qa_type: str, interval_index: int) -> Path:
    return agent_workdir / "agent-output" / qa_type / f"qa_{interval_index}.json"


def qa_timestamp(row: dict[str, Any]) -> Any:
    return row.get("end_utc") or row.get("end_local") or row.get("end_ts")


def qa_timestamp_ts(row: dict[str, Any]) -> float:
    parsed = parse_timestamp(row.get("end_ts"))
    if parsed is None:
        parsed = parse_timestamp(qa_timestamp(row))
    if parsed is None:
        raise RuntimeError(f"could not parse interval end timestamp: {row}")
    return parsed


def context_for_interval(
    indexed_events: list[dict[str, Any]],
    row: dict[str, Any],
) -> list[dict[str, Any]]:
    return context_events_for_timestamp(
        indexed_events,
        qa_timestamp_ts(row),
        QUESTION_CONTEXT_EVENT_COUNT,
    )


def extract_qa_pairs(data: Any) -> list[Any] | None:
    """Return qa_pairs from either the flat shape (`qa_pairs` at top level)
    or the legacy threaded shape (`threads[*].qa_pairs`).

    Returns None when neither shape is present so callers can distinguish
    "missing" from "empty".
    """
    if not isinstance(data, dict):
        return None
    flat = data.get("qa_pairs")
    if isinstance(flat, list):
        return flat
    threads = data.get("threads")
    if isinstance(threads, list):
        collected: list[Any] = []
        for thread in threads:
            if not isinstance(thread, dict):
                continue
            pairs = thread.get("qa_pairs")
            if isinstance(pairs, list):
                collected.extend(pairs)
        return collected
    return None


def attach_generic_qa_context(
    data: dict[str, Any],
    qa_type: str,
    row: dict[str, Any],
    context_events: list[dict[str, Any]],
) -> dict[str, Any]:
    output = dict(data)
    output["qa_type"] = qa_type
    output["qa_timestamp"] = qa_timestamp(row)
    output["qa_timestamp_ts"] = qa_timestamp_ts(row)
    output["interval"] = row
    output["context_events"] = context_events
    qa_pairs = extract_qa_pairs(output)
    if qa_pairs is not None:
        for pair in qa_pairs:
            if isinstance(pair, dict):
                pair.setdefault("category", qa_type)
        output["qa_pairs"] = qa_pairs
        output.pop("threads", None)
    return output


def normalize_generic_qa_file(
    path: Path,
    qa_type: str,
    row: dict[str, Any],
    context_events: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"generic QA output is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"generic QA output must be a JSON object: {path}")

    normalized = attach_generic_qa_context(data, qa_type, row, context_events)
    validate_generic_qa_data(normalized, path)
    if normalized != data:
        write_json_atomically(path, normalized)
    return normalized


def validate_generic_qa_data(data: Any, path: Path | str) -> None:
    if not isinstance(data, dict):
        raise RuntimeError(f"generic QA output must be a JSON object: {path}")

    qa_type = data.get("qa_type")
    if not isinstance(qa_type, str) or qa_type not in QA_TYPES:
        raise RuntimeError(f"generic QA output has invalid qa_type: {path}")

    cutoff_ts = parse_timestamp(data.get("qa_timestamp_ts"))
    if cutoff_ts is None:
        cutoff_ts = parse_timestamp(data.get("qa_timestamp"))
    if cutoff_ts is None:
        raise RuntimeError(f"generic QA output has invalid qa_timestamp: {path}")

    valid_indexes = valid_context_indexes(data, path, "generic QA")

    qa_pairs = extract_qa_pairs(data)
    if qa_pairs is None:
        raise RuntimeError(f"generic QA output must include qa_pairs: {path}")
    min_qa_pairs = 0 if qa_type in SPARSE_QA_TYPES else MIN_QAS_PER_INTERVAL
    if not (min_qa_pairs <= len(qa_pairs) <= MAX_QAS_PER_INTERVAL):
        raise RuntimeError(
            f"generic QA output qa_pairs must contain "
            f"{min_qa_pairs}-{MAX_QAS_PER_INTERVAL} entries, got "
            f"{len(qa_pairs)}: {path}"
        )

    for pair_index, pair in enumerate(qa_pairs):
        validate_grounded_pair(
            pair,
            pair_index,
            f"qa_pairs[{pair_index}]",
            cutoff_ts,
            valid_indexes,
            path,
            "generic QA",
            "qa_timestamp",
        )


def print_generic_qa_dry_run(
    args: argparse.Namespace,
    template: str,
    qa_type: str,
    row: dict[str, Any],
    indexed_events: list[dict[str, Any]],
) -> None:
    interval_index = int(row["interval_index"])
    output_path = qa_path(args, qa_type, interval_index)
    context_events = context_for_interval(indexed_events, row)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            f"generic-qa-{qa_type}-{interval_index}",
        )
        isolated_workdir = agent_workdir
        agent_output_path = agent_qa_path(agent_workdir, qa_type, interval_index)
    agent_output_path.parent.mkdir(parents=True, exist_ok=True)

    provider = build_provider_command(args, agent_workdir)
    prompt = render_generic_qa_prompt(
        template,
        qa_type,
        row,
        context_events,
        agent_output_path,
        provider.name,
        args.pairs_per_run,
    )
    print(f"\n--- generic QA {qa_type} interval {interval_index} ---")
    print(f"generic QA path: {output_path}")
    print(f"context events: {len(context_events)}")
    print(f"agent QA path: {agent_output_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def run_generic_qa_once(
    args: argparse.Namespace,
    template: str,
    qa_type: str,
    row: dict[str, Any],
    indexed_events: list[dict[str, Any]],
) -> GenericQAResult:
    interval_index = int(row["interval_index"])
    output_path = qa_path(args, qa_type, interval_index)
    context_events = context_for_interval(indexed_events, row)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            f"generic-qa-{qa_type}-{interval_index}",
        )
        isolated_workdir = agent_workdir
        agent_output_path = agent_qa_path(agent_workdir, qa_type, interval_index)

    stdout_path, stderr_path = agent_log_paths(
        args.generic_qa_dir / qa_type,
        f"qa_{interval_index}",
        args.provider,
    )
    prompt = render_generic_qa_prompt(
        template,
        qa_type,
        row,
        context_events,
        agent_output_path,
        args.provider,
        args.pairs_per_run,
    )
    job = run_agent_job(
        args,
        agent_workdir=agent_workdir,
        isolated_workdir=isolated_workdir,
        prompt=prompt,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        prefix=f"{args.provider}:generic-qa:{qa_type}:{interval_index}",
        log_message=f"generic QA {qa_type} interval {interval_index} -> {output_path}",
        output_path=output_path,
        agent_output_path=agent_output_path,
    )

    if job.returncode == 0 and output_path.exists():
        normalize_generic_qa_file(output_path, qa_type, row, context_events)

    record = {
        "provider": job.provider.name,
        "mode": "generic_qa",
        "qa_type": qa_type,
        "discovery_dir": str(args.discovery_dir),
        "generic_qa_dir": str(args.generic_qa_dir),
        "interval_index": interval_index,
        "qa_path": str(output_path),
        "question_context_event_count": len(context_events),
        "agent_isolated": not args.no_isolate_agent_workdir,
        "agent_visible_roots": ["logs-indexed", "agent-output"]
        if not args.no_isolate_agent_workdir
        else ["repo_root"],
        "stdout_path": str(job.stdout_path),
        "stderr_path": str(job.stderr_path),
        "returncode": job.returncode,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "model": job.provider.model,
        "effort": job.provider.effort,
        "sandbox": job.provider.sandbox,
    }
    return GenericQAResult(
        qa_type=qa_type,
        interval_index=interval_index,
        record=record,
        qa_path=output_path,
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        created_qa=job.created_output,
    )


def iter_generic_qa_files(generic_qa_dir: Path) -> list[tuple[str, int, Path]]:
    files: list[tuple[str, int, Path]] = []
    for qa_type in QA_TYPES:
        type_dir = generic_qa_dir / qa_type
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("qa_*.json")):
            try:
                interval_index = int(path.stem[len("qa_") :])
            except ValueError:
                continue
            files.append((qa_type, interval_index, path))
    files.sort(key=lambda item: (item[1], item[0]))
    return files


def remove_stale_final_if_needed(path: Path) -> None:
    if path.exists():
        path.unlink()


def interval_indexes_slug(raw: str) -> str:
    return selector_slug(raw)


def final_generic_qa_path(args: argparse.Namespace) -> Path:
    return args.generic_qa_dir / "final_qa.json"


def selected_final_interval_indexes(args: argparse.Namespace) -> set[int] | None:
    interval_indexes = getattr(args, "interval_indexes", None)
    days = getattr(args, "days", None)
    intervals = getattr(args, "intervals", None)
    if not interval_indexes and not days:
        return None
    if intervals is None:
        return None
    rows = select_rows(
        read_jsonl(intervals),
        interval_indexes,
        days,
        getattr(args, "start", 0),
        getattr(args, "limit", None),
    )
    return {
        int(row["interval_index"])
        for row in rows
        if isinstance(row.get("interval_index"), int)
    }


def write_final_generic_qa(args: argparse.Namespace) -> None:
    final_items: list[dict[str, Any]] = []
    selected_indexes = selected_final_interval_indexes(args)
    for qa_type, interval_index, path in iter_generic_qa_files(args.generic_qa_dir):
        if selected_indexes is not None and interval_index not in selected_indexes:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"generic QA output is not valid JSON: {path}: {exc}") from exc
        validate_generic_qa_data(data, path)
        final_items.append(
            {
                "qa_type": qa_type,
                "interval_index": interval_index,
                "qa_timestamp": data.get("qa_timestamp"),
                "context_events": data.get("context_events"),
                "qa": data,
            }
        )

    final_path = final_generic_qa_path(args)
    if not final_items:
        remove_stale_final_if_needed(final_path)
        print(f"no generic QA files found under {args.generic_qa_dir}", file=sys.stderr)
        return
    write_json_atomically(final_path, final_items)
    print(f"wrote final generic QA -> {final_path}", file=sys.stderr)


def cleanup_empty_generic_qa_dirs(args: argparse.Namespace) -> None:
    if not args.generic_qa_dir.exists():
        return
    for qa_type in QA_TYPES:
        type_dir = args.generic_qa_dir / qa_type
        if type_dir.is_dir() and not any(type_dir.iterdir()):
            shutil.rmtree(type_dir)


def run(args: argparse.Namespace) -> int:
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")
    if not args.intervals.exists():
        raise SystemExit(f"interval JSONL not found: {args.intervals}")

    rows = select_rows(
        read_jsonl(args.intervals),
        args.interval_indexes,
        args.days,
        args.start,
        args.limit,
    )
    if not rows:
        print("no rows selected", file=sys.stderr)
        return 0

    indexed_events = load_indexed_events(args.repo_root / "logs-indexed")
    if not indexed_events:
        raise SystemExit(f"no timestamped events found in {args.repo_root / 'logs-indexed'}")

    templates = {
        qa_type: load_generic_qa_template(args, qa_type)
        for qa_type in args.qa_types
    }

    selected: list[tuple[str, dict[str, Any]]] = [
        (qa_type, row) for row in rows for qa_type in args.qa_types
    ]

    print(f"selected intervals: {len(rows)}", file=sys.stderr)
    print(f"selected generic QA runs: {len(selected)}", file=sys.stderr)
    print(f"qa types: {', '.join(args.qa_types)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    print(f"jobs: {args.jobs}", file=sys.stderr)
    print(
        f"question context events per run: {QUESTION_CONTEXT_EVENT_COUNT}",
        file=sys.stderr,
    )

    selected_to_run: list[tuple[str, dict[str, Any]]] = []
    for qa_type, row in selected:
        interval_index = int(row["interval_index"])
        output_path = qa_path(args, qa_type, interval_index)
        if output_path.exists() and not args.force:
            if not args.dry_run:
                context_events = context_for_interval(indexed_events, row)
                normalize_generic_qa_file(output_path, qa_type, row, context_events)
            print(
                f"skip generic QA {qa_type} interval {interval_index}: "
                f"{output_path} exists",
                file=sys.stderr,
            )
            continue
        if args.dry_run:
            print_generic_qa_dry_run(
                args,
                templates[qa_type],
                qa_type,
                row,
                indexed_events,
            )
        else:
            selected_to_run.append((qa_type, row))

    if args.dry_run:
        cleanup_empty_generic_qa_dirs(args)
        return 0

    if not selected_to_run:
        write_final_generic_qa(args)
        return 0

    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_item = {
            executor.submit(
                run_generic_qa_once,
                args,
                templates[qa_type],
                qa_type,
                row,
                indexed_events,
            ): (qa_type, int(row["interval_index"]))
            for qa_type, row in selected_to_run
        }
        for future in as_completed(future_to_item):
            qa_type, interval_index = future_to_item[future]
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                print(
                    f"generic QA {qa_type} interval {interval_index} failed: {exc}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_item:
                        pending.cancel()
                    return 1
                continue

            append_jsonl(args.run_log, result.record)
            if result.returncode != 0:
                failures += 1
                print(
                    f"generic QA {result.qa_type} interval {result.interval_index} "
                    f"failed with exit code {result.returncode}; see {result.stderr_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_item:
                        pending.cancel()
                    return result.returncode

            if not result.created_qa:
                failures += 1
                print(
                    f"generic QA {result.qa_type} interval {result.interval_index} "
                    f"completed but did not create {result.qa_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_item:
                        pending.cancel()
                    return 1

    if failures:
        return 1
    write_final_generic_qa(args)
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
