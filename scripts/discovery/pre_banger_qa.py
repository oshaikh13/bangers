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
from .banger_manifest import write_combined_bangers_file
from .cli import add_claude_args, add_codex_args
from .intervals import parse_interval_indexes
from .io import append_jsonl, read_jsonl
from .paths import (
    DEFAULT_INTERVAL_MINUTES,
    DEFAULT_PRE_BANGER_QA_COMMON_TEMPLATE,
    DEFAULT_PRE_BANGER_QA_PROMPTS_DIR,
    DEFAULT_PRE_BANGER_SEED_FILTER_TEMPLATE,
    REPO_ROOT,
    default_discovery_dir,
    default_intervals_path,
)
from .prompts import (
    load_template,
    render_pre_banger_qa_prompt,
    render_pre_banger_seed_filter_prompt,
)
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


QA_TYPES = (
    "timing",
    "curiosity",
    "disregard",
    "threaded",
)
THREADED_QA_TYPE = "threaded"
MIN_QAS_PER_RUN = 3
MAX_QAS_PER_RUN = 10
THREAD_COUNT = 3
MIN_QAS_PER_THREAD = 3
MAX_QAS_PER_THREAD = 10


@dataclass(frozen=True)
class PreBangerQAResult:
    qa_type: str
    seed_id: str
    record: dict[str, Any]
    qa_path: Path
    stderr_path: Path
    returncode: int
    created_qa: bool


@dataclass(frozen=True)
class SeedFilterResult:
    record: dict[str, Any]
    output_path: Path
    stderr_path: Path
    returncode: int
    created_output: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run pipeline 20: cool pre-banger QA generation over "
            "prompt-ranked historical banger seeds."
        )
    )
    parser.add_argument(
        "--provider",
        choices=("codex", "claude"),
        default="codex",
        help="Agent CLI used for each pre-banger QA run.",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        help="Interval size used to derive the default discovery directory.",
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
        "--bangers-dir",
        help="Directory containing 03_bangers output. Defaults to <discovery-dir>/03_bangers.",
    )
    parser.add_argument(
        "--combined-bangers-path",
        help=(
            "Combined banger seed JSON used by the ranking prompt. Defaults to "
            "<bangers-dir>/combined_bangers.json."
        ),
    )
    parser.add_argument(
        "--pre-banger-qa-dir",
        help=(
            "Pipeline 20 output directory. Defaults to "
            "<discovery-dir>/20_pre_banger_qa."
        ),
    )
    parser.add_argument(
        "--run-log",
        help="JSONL run ledger. Defaults inside --discovery-dir.",
    )
    parser.add_argument(
        "--common-template",
        default=str(DEFAULT_PRE_BANGER_QA_COMMON_TEMPLATE),
        help="Shared prompt template for pipeline 20.",
    )
    parser.add_argument(
        "--seed-filter-template",
        default=str(DEFAULT_PRE_BANGER_SEED_FILTER_TEMPLATE),
        help="Prompt template used to rank seeds by usefulness and intervention value.",
    )
    parser.add_argument(
        "--seed-filter-path",
        help=(
            "JSON file containing prompt-ranked seeds. Defaults to "
            "<pre-banger-qa-dir>/seed_rankings.json."
        ),
    )
    parser.add_argument(
        "--force-seed-filter",
        action="store_true",
        help="Regenerate the prompt-ranked seed file even if it exists.",
    )
    parser.add_argument(
        "--prompts-dir",
        default=str(DEFAULT_PRE_BANGER_QA_PROMPTS_DIR),
        help="Directory containing prompts/20_pre_banger_<qa_type>.md files.",
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
        default=6,
        help="Number of Q/A pairs requested for single-turn QA types. Defaults to 6.",
    )
    parser.add_argument(
        "--seed-ids",
        help="Comma-separated seed ids to run, e.g. `29_0_0,25_0_0`.",
    )
    parser.add_argument(
        "--banger-input-indexes",
        dest="banger_input_indexes",
        help="Comma-separated 02c banger input indexes or ranges to include.",
    )
    parser.add_argument(
        "--combined-indexes",
        dest="banger_input_indexes",
        help="Deprecated alias for --banger-input-indexes.",
    )
    parser.add_argument(
        "--interval-indexes",
        help=(
            "Comma-separated interval indexes or ranges to include. A seed is "
            "included when its banger_timestamp falls inside one of these intervals."
        ),
    )
    parser.add_argument("--start", type=int, default=0, help="Start offset after ranking.")
    parser.add_argument("--limit", type=int, help="Maximum number of ranked seeds to run.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if the expected qa_<seed_id>.json output exists.",
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


def parse_seed_ids(raw: str | None) -> set[str] | None:
    if not raw:
        return None
    seed_ids = {part.strip() for part in raw.split(",") if part.strip()}
    if not seed_ids:
        raise SystemExit("--seed-ids must not be empty")
    return seed_ids


def banger_input_indexes_arg(args: argparse.Namespace) -> str | None:
    return getattr(args, "banger_input_indexes", None) or getattr(
        args,
        "combined_indexes",
        None,
    )


def interval_indexes_slug(raw: str) -> str:
    return (
        raw.strip()
        .replace(",", "_")
        .replace("-", "-")
        .replace(" ", "")
        or "selected"
    )


def default_seed_filter_path(pre_banger_qa_dir: Path) -> Path:
    return pre_banger_qa_dir / "seed_rankings.json"


def normalize_args(args: argparse.Namespace) -> None:
    interval_minutes = args.interval_minutes or DEFAULT_INTERVAL_MINUTES
    if interval_minutes <= 0:
        raise SystemExit("--interval-minutes must be greater than 0")
    if args.jobs <= 0:
        raise SystemExit("--jobs must be greater than 0")
    if args.pairs_per_run < MIN_QAS_PER_RUN:
        raise SystemExit(f"--pairs-per-run must be at least {MIN_QAS_PER_RUN}")
    if args.pairs_per_run > MAX_QAS_PER_RUN:
        raise SystemExit(f"--pairs-per-run must be at most {MAX_QAS_PER_RUN}")
    if args.startup_progress_every < 0:
        raise SystemExit("--startup-progress-every must be non-negative")

    args.repo_root = Path(args.repo_root).resolve()
    args.intervals = (
        Path(args.intervals)
        if args.intervals is not None
        else default_intervals_path(interval_minutes)
    ).resolve()
    args.discovery_dir = (
        Path(args.discovery_dir)
        if args.discovery_dir
        else default_discovery_dir(args.provider, interval_minutes)
    ).resolve()
    args.bangers_dir = (
        Path(args.bangers_dir) if args.bangers_dir else args.discovery_dir / "03_bangers"
    ).resolve()
    args.combined_bangers_path = (
        Path(args.combined_bangers_path)
        if args.combined_bangers_path
        else args.bangers_dir / "combined_bangers.json"
    ).resolve()
    args.pre_banger_qa_dir = (
        Path(args.pre_banger_qa_dir)
        if args.pre_banger_qa_dir
        else args.discovery_dir / "20_pre_banger_qa"
    ).resolve()
    args.run_log = (
        Path(args.run_log)
        if args.run_log
        else args.discovery_dir / f"{args.provider}_exec_runs.jsonl"
    ).resolve()
    args.common_template = Path(args.common_template).resolve()
    args.seed_filter_template = Path(args.seed_filter_template).resolve()
    args.seed_filter_path = (
        Path(args.seed_filter_path)
        if args.seed_filter_path
        else default_seed_filter_path(args.pre_banger_qa_dir)
    ).resolve()
    args.prompts_dir = Path(args.prompts_dir).resolve()
    args.qa_types = parse_qa_types(args.qa_types)
    args.seed_ids = parse_seed_ids(args.seed_ids)

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
    return args.prompts_dir / f"20_pre_banger_{qa_type}.md"


def load_pre_banger_qa_template(args: argparse.Namespace, qa_type: str) -> str:
    common = load_template(
        args.common_template,
        (
            "{qa_type}",
            "{seed_json}",
            "{context_events_json}",
        ),
    )
    body_path = qa_type_template_path(args, qa_type)
    if not body_path.exists():
        raise SystemExit(f"pre-banger QA type prompt not found: {body_path}")
    return common + "\n\n" + body_path.read_text(encoding="utf-8")


def qa_path(args: argparse.Namespace, qa_type: str, seed_id: str) -> Path:
    return args.pre_banger_qa_dir / qa_type / f"qa_{seed_id}.json"


def agent_qa_path(agent_workdir: Path, qa_type: str, seed_id: str) -> Path:
    return agent_workdir / "agent-output" / qa_type / f"qa_{seed_id}.json"


def load_interval_filter_rows(args: argparse.Namespace) -> list[dict[str, Any]] | None:
    selected_indexes = parse_interval_indexes(args.interval_indexes)
    if selected_indexes is None:
        return None
    if not args.intervals.exists():
        raise SystemExit(f"interval JSONL not found: {args.intervals}")

    rows = [
        row
        for row in read_jsonl(args.intervals)
        if isinstance(row.get("interval_index"), int)
        and row["interval_index"] in selected_indexes
    ]
    if not rows:
        print("no interval rows selected", file=sys.stderr)
    return rows


def interval_bounds(row: dict[str, Any]) -> tuple[float, float]:
    start_ts = parse_timestamp(row.get("start_ts"))
    if start_ts is None:
        start_ts = parse_timestamp(row.get("start_utc") or row.get("start_local"))
    end_ts = parse_timestamp(row.get("end_ts"))
    if end_ts is None:
        end_ts = parse_timestamp(row.get("end_utc") or row.get("end_local"))
    if start_ts is None or end_ts is None:
        raise RuntimeError(f"could not parse interval bounds: {row}")
    return start_ts, end_ts


def seed_in_interval_rows(seed: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    seed_ts = parse_timestamp(seed.get("banger_timestamp"))
    if seed_ts is None:
        return False
    for row in rows:
        start_ts, end_ts = interval_bounds(row)
        if start_ts <= seed_ts <= end_ts:
            return True
    return False


def filter_seeds_by_interval_rows(
    seeds: list[dict[str, Any]],
    rows: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    if rows is None:
        return seeds
    return [seed for seed in seeds if seed_in_interval_rows(seed, rows)]


def seed_filter_path(args: argparse.Namespace) -> Path:
    return args.seed_filter_path


def agent_seed_filter_path(agent_workdir: Path) -> Path:
    return agent_workdir / "agent-output" / "seed_rankings.json"


def load_seed_filter_template(args: argparse.Namespace) -> str:
    return load_template(args.seed_filter_template, ("{combined_bangers_path}",))


def validate_seed_filter_data(data: Any, all_seeds: list[dict[str, Any]], path: Path | str) -> None:
    if not isinstance(data, dict):
        raise RuntimeError(f"pre-banger seed ranking output must be a JSON object: {path}")
    filtered = data.get("seeds")
    if not isinstance(filtered, list):
        raise RuntimeError(f"pre-banger seed ranking output must include seeds: {path}")

    all_seed_ids = {
        seed.get("seed_id")
        for seed in all_seeds
        if isinstance(seed.get("seed_id"), str)
    }
    seen: set[str] = set()
    for index, seed in enumerate(filtered):
        if not isinstance(seed, dict):
            raise RuntimeError(
                f"pre-banger seed ranking seeds[{index}] must be an object: {path}"
            )
        if "selection_label" in seed:
            raise RuntimeError(
                f"pre-banger seed ranking seeds[{index}] must not include "
                f"selection_label; use numeric usefulness scores instead: {path}"
            )
        seed_id = seed.get("seed_id")
        if not isinstance(seed_id, str) or not seed_id:
            raise RuntimeError(
                f"pre-banger seed ranking seeds[{index}].seed_id must be a string: {path}"
            )
        if seed_id not in all_seed_ids:
            raise RuntimeError(
                f"pre-banger seed ranking references unknown seed_id {seed_id}: {path}"
            )
        if seed_id in seen:
            raise RuntimeError(
                f"pre-banger seed ranking duplicates seed_id {seed_id}: {path}"
            )
        seen.add(seed_id)

        rank = seed.get("rank")
        if not isinstance(rank, int) or rank <= 0:
            raise RuntimeError(
                f"pre-banger seed ranking seeds[{index}].rank must be a "
                f"positive integer: {path}"
            )

        for score_key in (
            "user_value",
            "intervention_value_now",
            "engagement_pull",
            "surprise",
            "personal_relevance",
            "disregard",
            "grounding",
            "self_done_penalty",
        ):
            score = seed.get(score_key)
            if not isinstance(score, int) or not 1 <= score <= 10:
                raise RuntimeError(
                    f"pre-banger seed ranking seeds[{index}].{score_key} must "
                    f"be an integer from 1 to 10: {path}"
                )

        if seed.get("intervention_posture") not in {
            "surface_now",
            "wait",
            "stay_quiet",
        }:
            raise RuntimeError(
                f"pre-banger seed ranking seeds[{index}].intervention_posture "
                f"must be surface_now, wait, or stay_quiet: {path}"
            )
        if seed.get("negative_reason") not in {
            "none",
            "self_done",
            "obvious_next_step",
            "interruptive",
            "undergrounded",
            "stale",
        }:
            raise RuntimeError(
                f"pre-banger seed ranking seeds[{index}].negative_reason must "
                f"be none, self_done, obvious_next_step, interruptive, "
                f"undergrounded, or stale: {path}"
            )
        for text_key in (
            "timing_reason",
            "marginal_value_reason",
            "self_done_reason",
            "future_check",
        ):
            value = seed.get(text_key)
            if not isinstance(value, str) or not value:
                raise RuntimeError(
                    f"pre-banger seed ranking seeds[{index}].{text_key} must "
                    f"be a non-empty string: {path}"
                )


def load_seed_filter(path: Path, all_seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"pre-banger seed ranking not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"pre-banger seed ranking is not valid JSON: {path}: {exc}") from exc
    validate_seed_filter_data(data, all_seeds, path)

    seed_by_id = {
        seed["seed_id"]: seed
        for seed in all_seeds
        if isinstance(seed.get("seed_id"), str)
    }
    selected: list[dict[str, Any]] = []
    for filtered_seed in sorted(data["seeds"], key=lambda item: item["rank"]):
        seed = dict(seed_by_id[filtered_seed["seed_id"]])
        seed["ranking_metadata"] = filtered_seed
        seed["filter_metadata"] = filtered_seed
        selected.append(seed)
    return selected


def print_seed_filter_dry_run(
    args: argparse.Namespace,
    template: str,
    all_seeds: list[dict[str, Any]],
) -> None:
    output_path = seed_filter_path(args)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(args, "pre-banger-seed-filter")
        isolated_workdir = agent_workdir
        agent_output_path = agent_seed_filter_path(agent_workdir)
    agent_output_path.parent.mkdir(parents=True, exist_ok=True)

    provider = build_provider_command(args, agent_workdir)
    prompt = render_pre_banger_seed_filter_prompt(
        template,
        args.combined_bangers_path,
        agent_output_path,
        provider.name,
    )
    print("\n--- pre-banger seed ranking ---")
    print(f"seed ranking path: {output_path}")
    print(f"combined bangers path: {args.combined_bangers_path}")
    print(f"candidate seeds: {len(all_seeds)}")
    print(f"agent seed ranking path: {agent_output_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def run_seed_filter_once(
    args: argparse.Namespace,
    template: str,
    all_seeds: list[dict[str, Any]],
) -> SeedFilterResult:
    output_path = seed_filter_path(args)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(args, "pre-banger-seed-filter")
        isolated_workdir = agent_workdir
        agent_output_path = agent_seed_filter_path(agent_workdir)

    stdout_path, stderr_path = agent_log_paths(
        args.pre_banger_qa_dir,
        "seed_filter",
        args.provider,
    )
    prompt = render_pre_banger_seed_filter_prompt(
        template,
        args.combined_bangers_path,
        agent_output_path,
        args.provider,
    )
    job = run_agent_job(
        args,
        agent_workdir=agent_workdir,
        isolated_workdir=isolated_workdir,
        prompt=prompt,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        prefix=f"{args.provider}:pre-banger-seed-filter",
        log_message=f"pre-banger seed ranking -> {output_path}",
        output_path=output_path,
        agent_output_path=agent_output_path,
    )

    if job.returncode == 0 and output_path.exists():
        load_seed_filter(output_path, all_seeds)

    record = {
        "provider": job.provider.name,
        "mode": "pre_banger_seed_ranking",
        "discovery_dir": str(args.discovery_dir),
        "bangers_dir": str(args.bangers_dir),
        "combined_bangers_path": str(args.combined_bangers_path),
        "pre_banger_qa_dir": str(args.pre_banger_qa_dir),
        "seed_filter_path": str(output_path),
        "candidate_seed_count": len(all_seeds),
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
    return SeedFilterResult(
        record=record,
        output_path=output_path,
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        created_output=job.created_output,
    )


def select_filtered_seeds(
    args: argparse.Namespace,
    filtered: list[dict[str, Any]],
    interval_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    selected = filter_seeds_by_interval_rows(filtered, interval_rows)
    if args.seed_ids is not None:
        selected = [seed for seed in selected if seed.get("seed_id") in args.seed_ids]

    parsed_banger_input_indexes = parse_interval_indexes(banger_input_indexes_arg(args))
    if parsed_banger_input_indexes is not None:
        selected = [
            seed
            for seed in selected
            if isinstance(seed.get("combined_index"), int)
            and seed["combined_index"] in parsed_banger_input_indexes
        ]

    selected = selected[args.start :]
    if args.limit is not None:
        selected = selected[: args.limit]
    return selected


def context_for_seed(
    indexed_events: list[dict[str, Any]],
    seed: dict[str, Any],
) -> list[dict[str, Any]]:
    return context_events_for_timestamp(
        indexed_events,
        seed.get("banger_timestamp"),
        QUESTION_CONTEXT_EVENT_COUNT,
    )


def attach_pre_banger_context(
    data: dict[str, Any],
    qa_type: str,
    seed: dict[str, Any],
    context_events: list[dict[str, Any]],
) -> dict[str, Any]:
    output = dict(data)
    output["qa_type"] = qa_type
    output["seed_id"] = seed.get("seed_id")
    output["banger_timestamp"] = seed.get("banger_timestamp")
    output["target_banger"] = seed.get("target_banger", {})
    output["context_events"] = context_events

    if qa_type == THREADED_QA_TYPE:
        threads = output.get("threads")
        if isinstance(threads, list):
            for thread in threads:
                if not isinstance(thread, dict):
                    continue
                qa_pairs = thread.get("qa_pairs")
                if not isinstance(qa_pairs, list):
                    continue
                for pair in qa_pairs:
                    if isinstance(pair, dict):
                        pair.setdefault("category", "pre_banger_threaded")
    else:
        qa_pairs = output.get("qa_pairs")
        if isinstance(qa_pairs, list):
            for pair in qa_pairs:
                if isinstance(pair, dict):
                    pair.setdefault("category", f"pre_banger_{qa_type}")
    return output


def normalize_pre_banger_qa_file(
    path: Path,
    qa_type: str,
    seed: dict[str, Any],
    context_events: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"pre-banger QA output is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"pre-banger QA output must be a JSON object: {path}")

    normalized = attach_pre_banger_context(data, qa_type, seed, context_events)
    validate_pre_banger_qa_data(normalized, path)
    if normalized != data:
        write_json_atomically(path, normalized)
    return normalized


def validate_pre_banger_qa_data(data: Any, path: Path | str) -> None:
    if not isinstance(data, dict):
        raise RuntimeError(f"pre-banger QA output must be a JSON object: {path}")

    qa_type = data.get("qa_type")
    if not isinstance(qa_type, str) or qa_type not in QA_TYPES:
        raise RuntimeError(f"pre-banger QA output has invalid qa_type: {path}")

    cutoff_ts = parse_timestamp(data.get("banger_timestamp"))
    if cutoff_ts is None:
        raise RuntimeError(f"pre-banger QA output has invalid banger_timestamp: {path}")

    valid_indexes = valid_context_indexes(data, path, "pre-banger QA")

    if qa_type == THREADED_QA_TYPE:
        threads = data.get("threads")
        if not isinstance(threads, list) or len(threads) != THREAD_COUNT:
            raise RuntimeError(
                f"pre-banger threaded output must contain exactly {THREAD_COUNT} "
                f"threads: {path}"
            )
        for thread_index, thread in enumerate(threads):
            if not isinstance(thread, dict):
                raise RuntimeError(
                    f"pre-banger threaded output threads[{thread_index}] must be "
                    f"an object: {path}"
                )
            if thread.get("thread_id") != thread_index:
                raise RuntimeError(
                    f"pre-banger threaded output threads[{thread_index}].thread_id "
                    f"must equal {thread_index}: {path}"
                )
            qa_pairs = thread.get("qa_pairs")
            if not isinstance(qa_pairs, list) or not (
                MIN_QAS_PER_THREAD <= len(qa_pairs) <= MAX_QAS_PER_THREAD
            ):
                raise RuntimeError(
                    f"pre-banger threaded output threads[{thread_index}].qa_pairs "
                    f"must contain {MIN_QAS_PER_THREAD}-{MAX_QAS_PER_THREAD} "
                    f"entries: {path}"
                )
            for pair_index, pair in enumerate(qa_pairs):
                validate_grounded_pair(
                    pair,
                    pair_index,
                    f"threads[{thread_index}].qa_pairs[{pair_index}]",
                    cutoff_ts,
                    valid_indexes,
                    path,
                    "pre-banger QA",
                    "banger_timestamp",
                )
        return

    qa_pairs = data.get("qa_pairs")
    if not isinstance(qa_pairs, list) or not (
        MIN_QAS_PER_RUN <= len(qa_pairs) <= MAX_QAS_PER_RUN
    ):
        raise RuntimeError(
            f"pre-banger QA output qa_pairs must contain "
            f"{MIN_QAS_PER_RUN}-{MAX_QAS_PER_RUN} entries: {path}"
        )

    for pair_index, pair in enumerate(qa_pairs):
        validate_grounded_pair(
            pair,
            pair_index,
            f"qa_pairs[{pair_index}]",
            cutoff_ts,
            valid_indexes,
            path,
            "pre-banger QA",
            "banger_timestamp",
        )


def print_pre_banger_qa_dry_run(
    args: argparse.Namespace,
    template: str,
    qa_type: str,
    seed: dict[str, Any],
    indexed_events: list[dict[str, Any]],
) -> None:
    seed_id = str(seed["seed_id"])
    output_path = qa_path(args, qa_type, seed_id)
    context_events = context_for_seed(indexed_events, seed)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            f"pre-banger-qa-{qa_type}-{seed_id}",
        )
        isolated_workdir = agent_workdir
        agent_output_path = agent_qa_path(agent_workdir, qa_type, seed_id)
    agent_output_path.parent.mkdir(parents=True, exist_ok=True)

    provider = build_provider_command(args, agent_workdir)
    prompt = render_pre_banger_qa_prompt(
        template,
        qa_type,
        seed,
        context_events,
        agent_output_path,
        provider.name,
        args.pairs_per_run,
    )
    print(f"\n--- pre-banger QA {qa_type} seed {seed_id} ---")
    print(f"pre-banger QA path: {output_path}")
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


def run_pre_banger_qa_once(
    args: argparse.Namespace,
    template: str,
    qa_type: str,
    seed: dict[str, Any],
    indexed_events: list[dict[str, Any]],
) -> PreBangerQAResult:
    seed_id = str(seed["seed_id"])
    output_path = qa_path(args, qa_type, seed_id)
    context_events = context_for_seed(indexed_events, seed)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            f"pre-banger-qa-{qa_type}-{seed_id}",
        )
        isolated_workdir = agent_workdir
        agent_output_path = agent_qa_path(agent_workdir, qa_type, seed_id)

    stdout_path, stderr_path = agent_log_paths(
        args.pre_banger_qa_dir / qa_type,
        f"qa_{seed_id}",
        args.provider,
    )
    prompt = render_pre_banger_qa_prompt(
        template,
        qa_type,
        seed,
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
        prefix=f"{args.provider}:pre-banger-qa:{qa_type}:{seed_id}",
        log_message=f"pre-banger QA {qa_type} seed {seed_id} -> {output_path}",
        output_path=output_path,
        agent_output_path=agent_output_path,
    )

    if job.returncode == 0 and output_path.exists():
        normalize_pre_banger_qa_file(output_path, qa_type, seed, context_events)

    record = {
        "provider": job.provider.name,
        "mode": "pre_banger_qa",
        "qa_type": qa_type,
        "seed_id": seed_id,
        "discovery_dir": str(args.discovery_dir),
        "bangers_dir": str(args.bangers_dir),
        "pre_banger_qa_dir": str(args.pre_banger_qa_dir),
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
    return PreBangerQAResult(
        qa_type=qa_type,
        seed_id=seed_id,
        record=record,
        qa_path=output_path,
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        created_qa=job.created_output,
    )


def iter_pre_banger_qa_files(pre_banger_qa_dir: Path) -> list[tuple[str, str, Path]]:
    files: list[tuple[str, str, Path]] = []
    for qa_type in QA_TYPES:
        type_dir = pre_banger_qa_dir / qa_type
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("qa_*.json")):
            seed_id = path.stem[len("qa_") :]
            files.append((qa_type, seed_id, path))
    files.sort(key=lambda item: (item[1], item[0]))
    return files


def remove_stale_final_if_needed(path: Path) -> None:
    if path.exists():
        path.unlink()


def final_pre_banger_qa_path(args: argparse.Namespace) -> Path:
    interval_indexes = getattr(args, "interval_indexes", None)
    if interval_indexes:
        return args.pre_banger_qa_dir / f"final_qa_intervals_{interval_indexes_slug(interval_indexes)}.json"
    return args.pre_banger_qa_dir / "final_qa.json"


def write_final_pre_banger_qa(args: argparse.Namespace) -> None:
    final_items: list[dict[str, Any]] = []
    for qa_type, seed_id, path in iter_pre_banger_qa_files(args.pre_banger_qa_dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"pre-banger QA output is not valid JSON: {path}: {exc}") from exc
        validate_pre_banger_qa_data(data, path)
        final_items.append(
            {
                "qa_type": qa_type,
                "seed_id": seed_id,
                "banger_timestamp": data.get("banger_timestamp"),
                "context_events": data.get("context_events"),
                "qa": data,
            }
        )

    final_path = final_pre_banger_qa_path(args)
    if not final_items:
        remove_stale_final_if_needed(final_path)
        print(
            f"no pre-banger QA files found under {args.pre_banger_qa_dir}",
            file=sys.stderr,
        )
        return
    write_json_atomically(final_path, final_items)
    print(f"wrote final pre-banger QA -> {final_path}", file=sys.stderr)


def cleanup_empty_pre_banger_qa_dirs(args: argparse.Namespace) -> None:
    if not args.pre_banger_qa_dir.exists():
        return
    for qa_type in QA_TYPES:
        type_dir = args.pre_banger_qa_dir / qa_type
        if type_dir.is_dir() and not any(type_dir.iterdir()):
            shutil.rmtree(type_dir)


def run(args: argparse.Namespace) -> int:
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")

    combined_bangers = write_combined_bangers_file(
        args.combined_bangers_path,
        args.bangers_dir,
    )
    all_seeds = combined_bangers["seeds"]
    if not all_seeds:
        raise SystemExit(f"no banger seeds found in {args.bangers_dir}")
    interval_rows = load_interval_filter_rows(args)

    seed_filter_template = load_seed_filter_template(args)
    if args.dry_run and (args.force_seed_filter or not seed_filter_path(args).exists()):
        print_seed_filter_dry_run(args, seed_filter_template, all_seeds)
        return 0

    ranked: list[dict[str, Any]] | None = None
    needs_seed_ranking = args.force_seed_filter or not seed_filter_path(args).exists()
    if not needs_seed_ranking:
        try:
            ranked = load_seed_filter(seed_filter_path(args), all_seeds)
        except RuntimeError as exc:
            if args.dry_run:
                raise
            print(
                f"existing pre-banger seed ranking is stale or invalid; "
                f"regenerating. Reason: {exc}",
                file=sys.stderr,
            )
            needs_seed_ranking = True

    if needs_seed_ranking:
        result = run_seed_filter_once(args, seed_filter_template, all_seeds)
        append_jsonl(args.run_log, result.record)
        if result.returncode != 0:
            print(
                f"pre-banger seed ranking failed with exit code {result.returncode}; "
                f"see {result.stderr_path}",
                file=sys.stderr,
            )
            return result.returncode
        if not result.created_output:
            print(
                f"pre-banger seed ranking completed but did not create "
                f"{result.output_path}",
                file=sys.stderr,
            )
            return 1
        ranked = load_seed_filter(seed_filter_path(args), all_seeds)

    if ranked is None:
        ranked = load_seed_filter(seed_filter_path(args), all_seeds)
    seeds = select_filtered_seeds(args, ranked, interval_rows)
    if not seeds:
        print("no pre-banger seeds selected", file=sys.stderr)
        return 0

    indexed_events = load_indexed_events(args.repo_root / "logs-indexed")
    if not indexed_events:
        raise SystemExit(f"no timestamped events found in {args.repo_root / 'logs-indexed'}")

    templates = {
        qa_type: load_pre_banger_qa_template(args, qa_type)
        for qa_type in args.qa_types
    }
    selected: list[tuple[str, dict[str, Any]]] = [
        (qa_type, seed) for seed in seeds for qa_type in args.qa_types
    ]

    print(f"candidate pre-banger seeds: {len(all_seeds)}", file=sys.stderr)
    if interval_rows is not None:
        print(f"selected intervals: {len(interval_rows)}", file=sys.stderr)
    print(f"prompt-ranked pre-banger seeds: {len(ranked)}", file=sys.stderr)
    print(f"selected pre-banger seeds: {len(seeds)}", file=sys.stderr)
    print(f"selected pre-banger QA runs: {len(selected)}", file=sys.stderr)
    print(f"qa types: {', '.join(args.qa_types)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    print(f"jobs: {args.jobs}", file=sys.stderr)
    print(
        f"question context events per seed: {QUESTION_CONTEXT_EVENT_COUNT}",
        file=sys.stderr,
    )

    selected_to_run: list[tuple[str, dict[str, Any]]] = []
    for qa_type, seed in selected:
        seed_id = str(seed["seed_id"])
        output_path = qa_path(args, qa_type, seed_id)
        if output_path.exists() and not args.force:
            if not args.dry_run:
                context_events = context_for_seed(indexed_events, seed)
                normalize_pre_banger_qa_file(output_path, qa_type, seed, context_events)
            print(
                f"skip pre-banger QA {qa_type} seed {seed_id}: {output_path} exists",
                file=sys.stderr,
            )
            continue
        if args.dry_run:
            print_pre_banger_qa_dry_run(
                args,
                templates[qa_type],
                qa_type,
                seed,
                indexed_events,
            )
        else:
            selected_to_run.append((qa_type, seed))

    if args.dry_run:
        cleanup_empty_pre_banger_qa_dirs(args)
        return 0

    if not selected_to_run:
        write_final_pre_banger_qa(args)
        return 0

    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_item = {
            executor.submit(
                run_pre_banger_qa_once,
                args,
                templates[qa_type],
                qa_type,
                seed,
                indexed_events,
            ): (qa_type, str(seed["seed_id"]))
            for qa_type, seed in selected_to_run
        }
        for future in as_completed(future_to_item):
            qa_type, seed_id = future_to_item[future]
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                print(
                    f"pre-banger QA {qa_type} seed {seed_id} failed: {exc}",
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
                    f"pre-banger QA {result.qa_type} seed {result.seed_id} "
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
                    f"pre-banger QA {result.qa_type} seed {result.seed_id} "
                    f"completed but did not create {result.qa_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_item:
                        pending.cancel()
                    return 1

    if failures:
        return 1
    write_final_pre_banger_qa(args)
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
