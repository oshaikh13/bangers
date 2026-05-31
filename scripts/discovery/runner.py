from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tqdm import tqdm

from .agent_job import cleanup_isolated_workdir, copy_file_atomically, run_agent_job
from .intervals import parse_interval_indexes, select_rows
from .io import append_jsonl, read_jsonl
from .qa_validation import (
    require_text_fields,
    valid_context_indexes,
    validate_question_basis,
)
from .prompts import (
    load_template,
    render_bangers_batch_prompt,
    render_bangers_prompt,
    render_bridges_prompt,
    render_combine_prompt,
    render_discovery_prompt,
    render_questions_prompt,
)
from .question_context import (
    MAX_QAS_PER_THREAD,
    MIN_QAS_PER_THREAD,
    QUESTION_CONTEXT_EVENT_COUNT,
    THREAD_COUNT,
    context_events_for_timestamp,
    load_indexed_events,
)
from .providers import build_provider_command

SCREENSHOTS_DIR = "screenshots"


@dataclass(frozen=True)
class IntervalResult:
    interval_index: int
    record: dict[str, Any]
    goal_path: Path
    stderr_path: Path
    returncode: int
    created_goal: bool


@dataclass(frozen=True)
class CombineResult:
    record: dict[str, Any]
    combined_path: Path
    stderr_path: Path
    returncode: int
    created_combined: bool


@dataclass(frozen=True)
class BridgesResult:
    record: dict[str, Any]
    bridges_path: Path
    stderr_path: Path
    returncode: int
    created_bridges: bool


@dataclass(frozen=True)
class BangersResult:
    combined_index: int
    record: dict[str, Any]
    bangers_path: Path
    stderr_path: Path
    returncode: int
    created_bangers: bool


@dataclass(frozen=True)
class BangersBatchResult:
    input_indexes: list[int]
    record: dict[str, Any]
    bangers_paths: list[Path]
    stderr_path: Path
    returncode: int
    missing_paths: list[Path]


@dataclass(frozen=True)
class QuestionsResult:
    suggestion_index: str
    record: dict[str, Any]
    questions_path: Path
    stderr_path: Path
    returncode: int
    created_questions: bool


def iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            yield path, path.relative_to(root)


def count_files(root: Path) -> int:
    return sum(1 for _ in iter_files(root))


def hardlink_screenshot_tree(
    src: Path,
    dst: Path,
    label: str,
    progress_every: int,
) -> None:
    total = count_files(src)
    dst.mkdir(parents=True, exist_ok=True)
    miniters = progress_every or None
    files = iter_files(src)
    for src_file, rel_path in tqdm(
        files,
        total=total,
        desc=f"startup {label}",
        unit="img",
        miniters=miniters,
        mininterval=0.5,
        leave=False,
        file=sys.stderr,
    ):
        dst_file = dst / rel_path
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src_file, dst_file)
        except OSError as exc:
            raise RuntimeError(
                "failed to hardlink screenshots into isolated discovery "
                "workdir; not falling back to copy because that can "
                f"duplicate the screenshot corpus: {src} -> {dst}: {exc}"
            ) from exc


def symlink_screenshot_tree(src: Path, dst: Path, label: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(src, dst, target_is_directory=True)
    except OSError as exc:
        raise RuntimeError(
            f"failed to symlink screenshots into isolated discovery workdir: "
            f"{src} -> {dst}: {exc}"
        ) from exc
    tqdm.write(
        f"startup {label}: symlinked screenshots directory",
        file=sys.stderr,
    )


def copy_logs_indexed(
    src: Path,
    dst: Path,
    args: argparse.Namespace,
    label: str,
) -> None:
    if not src.exists():
        raise SystemExit(f"logs-indexed not found: {src}")

    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(".git", SCREENSHOTS_DIR),
    )

    src_screenshots = src / SCREENSHOTS_DIR
    if src_screenshots.exists():
        dst_screenshots = dst / SCREENSHOTS_DIR
        if args.screenshot_link_mode == "symlink":
            symlink_screenshot_tree(src_screenshots, dst_screenshots, label)
        else:
            hardlink_screenshot_tree(
                src_screenshots,
                dst_screenshots,
                label,
                args.startup_progress_every,
            )


def create_isolated_workdir(
    args: argparse.Namespace,
    label: str | int,
    *,
    include_logs_indexed: bool = True,
) -> Path:
    label = str(label)
    workdir = Path(
        tempfile.mkdtemp(prefix=f"discovery-{args.provider}-{label}-")
    ).resolve()
    if include_logs_indexed:
        copy_logs_indexed(
            args.repo_root / "logs-indexed",
            workdir / "logs-indexed",
            args,
            label,
        )
    (workdir / "agent-output").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    return workdir


def run_one_interval(
    args: argparse.Namespace,
    template: str,
    row: dict[str, Any],
) -> IntervalResult:
    interval_index = int(row["interval_index"])
    goal_path = args.goals_dir / f"goal_{interval_index}.json"
    stdout_path = args.goals_dir / f"goal_{interval_index}.stdout.log"
    stderr_path = args.goals_dir / f"goal_{interval_index}.stderr.log"

    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_goal_path = goal_path
    else:
        agent_workdir = create_isolated_workdir(args, interval_index)
        isolated_workdir = agent_workdir
        agent_goal_path = (
            agent_workdir / "agent-output" / f"goal_{interval_index}.json"
        )

    prompt = render_discovery_prompt(template, row, agent_goal_path, args.provider)
    job = run_agent_job(
        args,
        agent_workdir=agent_workdir,
        isolated_workdir=isolated_workdir,
        prompt=prompt,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        prefix=f"{args.provider}:{interval_index}",
        log_message=f"run interval {interval_index} -> {goal_path}",
        output_path=goal_path,
        agent_output_path=agent_goal_path,
    )
    record = {
        "provider": job.provider.name,
        "discovery_dir": str(args.discovery_dir),
        "goals_dir": str(args.goals_dir),
        "interval_index": interval_index,
        "goal_path": str(goal_path),
        "agent_goal_path": str(agent_goal_path),
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
    return IntervalResult(
        interval_index=interval_index,
        record=record,
        goal_path=goal_path,
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        created_goal=job.created_output,
    )


def validate_unique_interval_indexes(rows: list[dict[str, Any]]) -> None:
    seen: set[int] = set()
    duplicates: list[int] = []
    for row in rows:
        interval_index = int(row["interval_index"])
        if interval_index in seen:
            duplicates.append(interval_index)
        seen.add(interval_index)
    if duplicates:
        dupes = ", ".join(str(index) for index in sorted(set(duplicates)))
        raise SystemExit(f"duplicate interval indexes selected: {dupes}")


def print_dry_run(args: argparse.Namespace, template: str, row: dict[str, Any]) -> None:
    interval_index = int(row["interval_index"])
    goal_path = args.goals_dir / f"goal_{interval_index}.json"
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_goal_path = goal_path
    else:
        agent_workdir = create_isolated_workdir(args, interval_index)
        isolated_workdir = agent_workdir
        agent_goal_path = (
            agent_workdir / "agent-output" / f"goal_{interval_index}.json"
        )

    provider = build_provider_command(args, agent_workdir)
    prompt = render_discovery_prompt(template, row, agent_goal_path, provider.name)
    print(f"\n--- interval {interval_index} ---")
    print(f"goal path: {goal_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"agent goal path: {agent_goal_path}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def goal_files(goals_dir: Path) -> list[Path]:
    return sorted(goals_dir.glob("goal_*.json"))


def validate_combined_json(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"combined output is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, list):
        raise RuntimeError(f"combined output must be a JSON array: {path}")


def load_combined_json(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"combined input is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, list):
        raise RuntimeError(f"combined input must be a JSON array: {path}")

    elements: list[dict[str, Any]] = []
    for index, element in enumerate(data):
        if not isinstance(element, dict):
            raise RuntimeError(
                f"combined input element {index} must be a JSON object: {path}"
            )
        elements.append(element)
    return elements


def banger_inputs_path(args: argparse.Namespace) -> Path:
    return args.suggestion_inputs_dir / "inputs.json"


def banger_input_indexes_arg(args: argparse.Namespace) -> str | None:
    return getattr(args, "banger_input_indexes", None) or getattr(
        args,
        "combined_indexes",
        None,
    )


def select_banger_input_elements(
    elements: list[dict[str, Any]],
    banger_input_indexes: str | None,
    start: int,
    limit: int | None,
) -> list[tuple[int, dict[str, Any]]]:
    selected = list(enumerate(elements))
    parsed_indexes = parse_interval_indexes(banger_input_indexes)
    if parsed_indexes is not None:
        selected = [
            (index, element) for index, element in selected if index in parsed_indexes
        ]

    selected = selected[start:]
    if limit is not None:
        selected = selected[:limit]
    return selected


def validate_questions_json(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"questions output is not valid JSON: {path}: {exc}") from exc
    validate_questions_data(data, path)


def validate_questions_data(data: Any, path: Path | str) -> None:
    if not isinstance(data, dict):
        raise RuntimeError(f"questions output must be a JSON object: {path}")
    valid_indexes = valid_context_indexes(data, path, "questions")

    if "threads" not in data:
        raise RuntimeError(f"questions output must include threads: {path}")
    threads = data["threads"]
    if not isinstance(threads, list):
        raise RuntimeError(f"questions output threads must be an array: {path}")
    if len(threads) != THREAD_COUNT:
        raise RuntimeError(
            f"questions output threads must contain exactly {THREAD_COUNT} "
            f"entries, got {len(threads)}: {path}"
        )
    for thread_index, thread in enumerate(threads):
        if not isinstance(thread, dict):
            raise RuntimeError(
                f"questions output threads[{thread_index}] must be an object: {path}"
            )
        if thread.get("thread_id") != thread_index:
            raise RuntimeError(
                f"questions output threads[{thread_index}].thread_id must equal "
                f"{thread_index}: {path}"
            )
        qa_pairs = thread.get("qa_pairs")
        if not isinstance(qa_pairs, list):
            raise RuntimeError(
                f"questions output threads[{thread_index}].qa_pairs must be an "
                f"array: {path}"
            )
        if not (MIN_QAS_PER_THREAD <= len(qa_pairs) <= MAX_QAS_PER_THREAD):
            raise RuntimeError(
                f"questions output threads[{thread_index}].qa_pairs must contain "
                f"{MIN_QAS_PER_THREAD}-{MAX_QAS_PER_THREAD} entries, got "
                f"{len(qa_pairs)}: {path}"
            )
        for pair_index, pair in enumerate(qa_pairs):
            location = f"threads[{thread_index}].qa_pairs[{pair_index}]"
            if not isinstance(pair, dict):
                raise RuntimeError(
                    f"questions output {location} must be an object: {path}"
                )
            if pair.get("q_id") != pair_index:
                raise RuntimeError(
                    f"questions output {location}.q_id must equal "
                    f"{pair_index}: {path}"
                )
            for key in (
                "question",
                "answer",
                "question_basis",
                "why_it_matters",
                "evidence_grounding",
                "question_difficulty",
            ):
                if key not in pair:
                    raise RuntimeError(
                        f"questions output {location} must include {key}: {path}"
                    )
            require_text_fields(
                pair,
                (
                    "question",
                    "answer",
                    "why_it_matters",
                    "evidence_grounding",
                ),
                location,
                path,
                "questions",
            )
            if not isinstance(pair.get("question_difficulty"), (int, float)):
                raise RuntimeError(
                    f"questions output {location}.question_difficulty must "
                    f"be a number: {path}"
                )
            validate_question_basis(pair, location, valid_indexes, path, "questions")


def print_combine_dry_run(args: argparse.Namespace, template: str) -> None:
    isolated_workdir: Path | None = None
    combined_path = args.combined_dir / "combined.json"
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_goals_dir = args.goals_dir
        agent_combined_path = combined_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            "combine",
            include_logs_indexed=False,
        )
        isolated_workdir = agent_workdir
        agent_goals_dir = agent_workdir / "agent-input" / "goals"
        agent_goals_dir.mkdir(parents=True)
        for path in goal_files(args.goals_dir):
            copy_file_atomically(path, agent_goals_dir / path.name)
        agent_combined_path = agent_workdir / "agent-output" / "combined.json"

    provider = build_provider_command(args, agent_workdir)
    prompt = render_combine_prompt(
        template,
        agent_goals_dir,
        agent_combined_path,
        provider.name,
    )
    print("\n--- combine goals ---")
    print(f"goals dir: {args.goals_dir}")
    print(f"combined path: {combined_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"agent goals dir: {agent_goals_dir}")
    print(f"agent combined path: {agent_combined_path}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def run_combine_once(args: argparse.Namespace, template: str) -> CombineResult:
    combined_path = args.combined_dir / "combined.json"
    files = goal_files(args.goals_dir)

    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_goals_dir = args.goals_dir
        agent_combined_path = combined_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            "combine",
            include_logs_indexed=False,
        )
        isolated_workdir = agent_workdir
        agent_goals_dir = agent_workdir / "agent-input" / "goals"
        agent_goals_dir.mkdir(parents=True)
        for path in files:
            copy_file_atomically(path, agent_goals_dir / path.name)
        agent_combined_path = agent_workdir / "agent-output" / "combined.json"

    stdout_path = args.combined_dir / f"combined.{args.provider}.stdout.log"
    stderr_path = args.combined_dir / f"combined.{args.provider}.stderr.log"
    prompt = render_combine_prompt(
        template,
        agent_goals_dir,
        agent_combined_path,
        args.provider,
    )
    job = run_agent_job(
        args,
        agent_workdir=agent_workdir,
        isolated_workdir=isolated_workdir,
        prompt=prompt,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        prefix=f"{args.provider}:combine",
        log_message=f"combine {len(files)} goal files -> {combined_path}",
        output_path=combined_path,
        agent_output_path=agent_combined_path,
    )

    if job.returncode == 0 and combined_path.exists():
        validate_combined_json(combined_path)

    record = {
        "provider": job.provider.name,
        "mode": "combine",
        "discovery_dir": str(args.discovery_dir),
        "goals_dir": str(args.goals_dir),
        "combined_path": str(combined_path),
        "agent_isolated": not args.no_isolate_agent_workdir,
        "agent_visible_roots": ["agent-input", "agent-output"]
        if not args.no_isolate_agent_workdir
        else ["repo_root"],
        "goal_count": len(files),
        "stdout_path": str(job.stdout_path),
        "stderr_path": str(job.stderr_path),
        "returncode": job.returncode,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "model": job.provider.model,
        "effort": job.provider.effort,
        "sandbox": job.provider.sandbox,
    }
    return CombineResult(
        record=record,
        combined_path=combined_path,
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        created_combined=job.created_output,
    )


def run_combine(args: argparse.Namespace) -> int:
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")
    if not args.goals_dir.exists():
        raise SystemExit(f"goals directory not found: {args.goals_dir}")
    files = goal_files(args.goals_dir)
    if not files:
        raise SystemExit(f"no goal_*.json files found in {args.goals_dir}")

    template = load_template(args.template, ("{dir_name}", "{combined_path}"))
    combined_path = args.combined_dir / "combined.json"
    if combined_path.exists() and not args.force:
        print(f"skip combine: {combined_path} exists", file=sys.stderr)
        return 0

    print(f"selected goal files: {len(files)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    if args.dry_run:
        print_combine_dry_run(args, template)
        return 0

    args.combined_dir.mkdir(parents=True, exist_ok=True)
    result = run_combine_once(args, template)
    append_jsonl(args.run_log, result.record)
    if result.returncode != 0:
        print(
            f"combine failed with exit code {result.returncode}; "
            f"see {result.stderr_path}",
            file=sys.stderr,
        )
        return result.returncode
    if not result.created_combined:
        print(
            f"combine completed but did not create {result.combined_path}",
            file=sys.stderr,
        )
        return 1
    return 0


def validate_bridges_json(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"bridges output is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, list):
        raise RuntimeError(f"bridges output must be a JSON array: {path}")
    for index, bridge in enumerate(data):
        if not isinstance(bridge, dict):
            raise RuntimeError(f"bridges output element {index} must be an object: {path}")
        connected = bridge.get("connected_goals")
        if not isinstance(connected, list) or len(connected) < 2:
            raise RuntimeError(
                f"bridges output element {index} must include at least two "
                f"connected_goals: {path}"
            )


def print_bridges_dry_run(args: argparse.Namespace, template: str) -> None:
    combined_path = args.combined_dir / "combined.json"
    bridges_path = args.bridges_dir / "bridges.json"
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_combined_path = combined_path
        agent_bridges_path = bridges_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            "bridges",
            include_logs_indexed=False,
        )
        isolated_workdir = agent_workdir
        agent_combined_path = agent_workdir / "agent-input" / "combined.json"
        copy_file_atomically(combined_path, agent_combined_path)
        agent_bridges_path = agent_workdir / "agent-output" / "bridges.json"

    provider = build_provider_command(args, agent_workdir)
    prompt = render_bridges_prompt(
        template,
        agent_combined_path,
        agent_bridges_path,
        provider.name,
    )
    print("\n--- bridge goals ---")
    print(f"combined path: {combined_path}")
    print(f"bridges path: {bridges_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"agent combined path: {agent_combined_path}")
    print(f"agent bridges path: {agent_bridges_path}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def run_bridges_once(args: argparse.Namespace, template: str) -> BridgesResult:
    combined_path = args.combined_dir / "combined.json"
    bridges_path = args.bridges_dir / "bridges.json"
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_combined_path = combined_path
        agent_bridges_path = bridges_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            "bridges",
            include_logs_indexed=False,
        )
        isolated_workdir = agent_workdir
        agent_combined_path = agent_workdir / "agent-input" / "combined.json"
        copy_file_atomically(combined_path, agent_combined_path)
        agent_bridges_path = agent_workdir / "agent-output" / "bridges.json"

    stdout_path = args.bridges_dir / f"bridges.{args.provider}.stdout.log"
    stderr_path = args.bridges_dir / f"bridges.{args.provider}.stderr.log"
    prompt = render_bridges_prompt(
        template,
        agent_combined_path,
        agent_bridges_path,
        args.provider,
    )
    job = run_agent_job(
        args,
        agent_workdir=agent_workdir,
        isolated_workdir=isolated_workdir,
        prompt=prompt,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        prefix=f"{args.provider}:bridges",
        log_message=f"bridge {combined_path} -> {bridges_path}",
        output_path=bridges_path,
        agent_output_path=agent_bridges_path,
    )

    if job.returncode == 0 and bridges_path.exists():
        validate_bridges_json(bridges_path)

    record = {
        "provider": job.provider.name,
        "mode": "bridges",
        "discovery_dir": str(args.discovery_dir),
        "combined_path": str(combined_path),
        "bridges_path": str(bridges_path),
        "agent_isolated": not args.no_isolate_agent_workdir,
        "agent_visible_roots": ["agent-input", "agent-output"]
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
    return BridgesResult(
        record=record,
        bridges_path=bridges_path,
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        created_bridges=job.created_output,
    )


def run_bridges(args: argparse.Namespace) -> int:
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")

    combined_path = args.combined_dir / "combined.json"
    if not combined_path.exists():
        raise SystemExit(f"combined.json not found: {combined_path}")

    template = load_template(args.template, ("{combined_path}", "{bridges_path}"))
    bridges_path = args.bridges_dir / "bridges.json"
    if bridges_path.exists() and not args.force:
        print(f"skip bridges: {bridges_path} exists", file=sys.stderr)
        return 0

    print(f"combined path: {combined_path}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    if args.dry_run:
        print_bridges_dry_run(args, template)
        return 0

    args.bridges_dir.mkdir(parents=True, exist_ok=True)
    result = run_bridges_once(args, template)
    append_jsonl(args.run_log, result.record)
    if result.returncode != 0:
        print(
            f"bridges failed with exit code {result.returncode}; "
            f"see {result.stderr_path}",
            file=sys.stderr,
        )
        return result.returncode
    if not result.created_bridges:
        print(
            f"bridges completed but did not create {result.bridges_path}",
            file=sys.stderr,
        )
        return 1
    return 0


def bangers_path(args: argparse.Namespace, combined_index: int) -> Path:
    return args.bangers_dir / f"banger_{combined_index}.json"


def agent_bangers_path(agent_workdir: Path, combined_index: int) -> Path:
    return agent_workdir / "agent-output" / f"banger_{combined_index}.json"


def bangers_batch_path(args: argparse.Namespace, input_indexes: list[int]) -> Path:
    return args.bangers_dir / f"bangers_{input_indexes[0]}_{input_indexes[-1]}.json"


def agent_bangers_batch_path(agent_workdir: Path, input_indexes: list[int]) -> Path:
    return (
        agent_workdir
        / "agent-output"
        / f"bangers_{input_indexes[0]}_{input_indexes[-1]}.json"
    )


def validate_banger_goals(goals: Any, path: Path) -> None:
    if not isinstance(goals, list):
        raise RuntimeError(f"bangers output goals must be an array: {path}")
    for goal_index, goal in enumerate(goals):
        if not isinstance(goal, dict):
            raise RuntimeError(
                f"bangers output goals[{goal_index}] must be an object: {path}"
            )
        opportunities = goal.get("opportunities")
        if not isinstance(opportunities, list):
            raise RuntimeError(
                f"bangers output goals[{goal_index}].opportunities must be "
                f"an array: {path}"
            )


def validate_bangers_json(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"bangers output is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"bangers output must be a JSON object: {path}")
    if "bangers" in data:
        bangers = data.get("bangers")
        if not isinstance(bangers, list):
            raise RuntimeError(f"bangers output bangers must be an array: {path}")
        for item_index, item in enumerate(bangers):
            if not isinstance(item, dict):
                raise RuntimeError(
                    f"bangers output bangers[{item_index}] must be an object: {path}"
                )
            if not isinstance(item.get("input_index"), int):
                raise RuntimeError(
                    f"bangers output bangers[{item_index}].input_index must be "
                    f"an integer: {path}"
                )
            validate_banger_goals(item.get("goals"), path)
    else:
        validate_banger_goals(data.get("goals"), path)


def split_bangers_batch_json(path: Path) -> list[tuple[int, dict[str, Any]]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"bangers input is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"bangers input must be a JSON object: {path}")
    if "bangers" not in data:
        try:
            combined_index = int(path.stem[len("banger_") :])
        except ValueError as exc:
            raise RuntimeError(
                f"legacy banger file is missing numeric index: {path}"
            ) from exc
        return [(combined_index, data)]

    bangers = data.get("bangers")
    if not isinstance(bangers, list):
        raise RuntimeError(f"bangers input bangers must be an array: {path}")
    items: list[tuple[int, dict[str, Any]]] = []
    for item_index, item in enumerate(bangers):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"bangers input bangers[{item_index}] must be an object: {path}"
            )
        input_index = item.get("input_index")
        if not isinstance(input_index, int):
            raise RuntimeError(
                f"bangers input bangers[{item_index}].input_index must be "
                f"an integer: {path}"
            )
        items.append((input_index, item))
    return items


def print_bangers_dry_run(
    args: argparse.Namespace,
    template: str,
    input_index: int,
    input_element: dict[str, Any],
) -> None:
    output_path = bangers_path(args, input_index)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(args, f"bangers-{input_index}")
        isolated_workdir = agent_workdir
        agent_output_path = agent_bangers_path(agent_workdir, input_index)

    provider = build_provider_command(args, agent_workdir)
    prompt = render_bangers_prompt(
        template,
        input_element,
        agent_output_path,
        provider.name,
    )
    print(f"\n--- banger input {input_index} ---")
    print(f"banger input path: {banger_inputs_path(args)}")
    print(f"input type: {input_element.get('type', 'goal')}")
    print(f"bangers path: {output_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"agent bangers path: {agent_output_path}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def banger_batch_log_stem(input_indexes: list[int]) -> str:
    if len(input_indexes) == 1:
        return f"banger_{input_indexes[0]}"
    return f"banger_batch_{input_indexes[0]}-{input_indexes[-1]}"


def banger_batches(
    selected: list[tuple[int, dict[str, Any]]],
    batch_size: int,
) -> list[list[tuple[int, dict[str, Any]]]]:
    return [
        selected[index : index + batch_size]
        for index in range(0, len(selected), batch_size)
    ]


def banger_batch_prompt_elements(
    batch: list[tuple[int, dict[str, Any]]],
) -> list[dict[str, Any]]:
    return [
        {
            "input_index": input_index,
            "input": input_element,
        }
        for input_index, input_element in batch
    ]


def print_bangers_batch_dry_run(
    args: argparse.Namespace,
    template: str,
    batch: list[tuple[int, dict[str, Any]]],
) -> None:
    input_indexes = [input_index for input_index, _ in batch]
    output_path = bangers_batch_path(args, input_indexes)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        label = (
            f"bangers-{input_indexes[0]}"
            if len(input_indexes) == 1
            else f"bangers-{input_indexes[0]}-{input_indexes[-1]}"
        )
        agent_workdir = create_isolated_workdir(args, label)
        isolated_workdir = agent_workdir
        agent_output_path = agent_bangers_batch_path(agent_workdir, input_indexes)

    provider = build_provider_command(args, agent_workdir)
    prompt = render_bangers_batch_prompt(
        template,
        {
            "output_path": str(agent_output_path),
            "items": banger_batch_prompt_elements(batch),
        },
        provider.name,
    )
    print(f"\n--- banger inputs {input_indexes[0]}-{input_indexes[-1]} ---")
    print(f"banger input path: {banger_inputs_path(args)}")
    print(f"batch size: {len(batch)}")
    print(f"bangers path: {output_path}")
    print(f"agent bangers path: {agent_output_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def run_bangers_once(
    args: argparse.Namespace,
    template: str,
    input_index: int,
    input_element: dict[str, Any],
) -> BangersResult:
    output_path = bangers_path(args, input_index)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(args, f"bangers-{input_index}")
        isolated_workdir = agent_workdir
        agent_output_path = agent_bangers_path(agent_workdir, input_index)

    stdout_path = args.bangers_dir / f"banger_{input_index}.{args.provider}.stdout.log"
    stderr_path = args.bangers_dir / f"banger_{input_index}.{args.provider}.stderr.log"
    prompt = render_bangers_prompt(
        template,
        input_element,
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
        prefix=f"{args.provider}:bangers:{input_index}",
        log_message=f"bangers input {input_index} -> {output_path}",
        output_path=output_path,
        agent_output_path=agent_output_path,
    )

    if job.returncode == 0 and output_path.exists():
        validate_bangers_json(output_path)

    record = {
        "provider": job.provider.name,
        "mode": "bangers",
        "discovery_dir": str(args.discovery_dir),
        "goals_dir": str(args.goals_dir),
        "combined_path": str(args.combined_dir / "combined.json"),
        "banger_input_path": str(banger_inputs_path(args)),
        "banger_input_index": input_index,
        "input_type": input_element.get("type", "goal"),
        "source_index": input_element.get("source_index", input_index),
        "combined_index": input_index,
        "bangers_path": str(output_path),
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
    return BangersResult(
        combined_index=input_index,
        record=record,
        bangers_path=output_path,
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        created_bangers=job.created_output,
    )


def run_bangers_batch_once(
    args: argparse.Namespace,
    template: str,
    batch: list[tuple[int, dict[str, Any]]],
) -> BangersBatchResult:
    input_indexes = [input_index for input_index, _ in batch]
    output_path = bangers_batch_path(args, input_indexes)
    if len(input_indexes) == 1:
        label = str(input_indexes[0])
        workdir_label = f"bangers-{input_indexes[0]}"
    else:
        label = f"{input_indexes[0]}-{input_indexes[-1]}"
        workdir_label = f"bangers-{input_indexes[0]}-{input_indexes[-1]}"

    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(args, workdir_label)
        isolated_workdir = agent_workdir
        agent_output_path = agent_bangers_batch_path(agent_workdir, input_indexes)

    log_stem = banger_batch_log_stem(input_indexes)
    stdout_path = args.bangers_dir / f"{log_stem}.{args.provider}.stdout.log"
    stderr_path = args.bangers_dir / f"{log_stem}.{args.provider}.stderr.log"
    prompt = render_bangers_batch_prompt(
        template,
        {
            "output_path": str(agent_output_path),
            "items": banger_batch_prompt_elements(batch),
        },
        args.provider,
    )
    job = run_agent_job(
        args,
        agent_workdir=agent_workdir,
        isolated_workdir=isolated_workdir,
        prompt=prompt,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        prefix=f"{args.provider}:bangers:{label}",
        log_message=f"bangers inputs {label} -> {args.bangers_dir}",
        output_path=output_path,
        agent_output_path=agent_output_path,
    )

    missing_paths = [] if output_path.exists() else [output_path]
    if job.returncode == 0 and output_path.exists():
        validate_bangers_json(output_path)

    record = {
        "provider": job.provider.name,
        "mode": "bangers",
        "discovery_dir": str(args.discovery_dir),
        "goals_dir": str(args.goals_dir),
        "combined_path": str(args.combined_dir / "combined.json"),
        "banger_input_path": str(banger_inputs_path(args)),
        "banger_input_indexes": input_indexes,
        "banger_batch_size": len(batch),
        "input_types": [
            input_element.get("type", "goal") for _, input_element in batch
        ],
        "source_indexes": [
            input_element.get("source_index", input_index)
            for input_index, input_element in batch
        ],
        "combined_indexes": input_indexes,
        "bangers_path": str(output_path),
        "bangers_paths": [str(output_path)],
        "agent_isolated": not args.no_isolate_agent_workdir,
        "agent_visible_roots": ["logs-indexed", "agent-output"]
        if not args.no_isolate_agent_workdir
        else ["repo_root"],
        "stdout_path": str(job.stdout_path),
        "stderr_path": str(job.stderr_path),
        "returncode": job.returncode,
        "missing_paths": [str(path) for path in missing_paths],
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "model": job.provider.model,
        "effort": job.provider.effort,
        "sandbox": job.provider.sandbox,
    }
    return BangersBatchResult(
        input_indexes=input_indexes,
        record=record,
        bangers_paths=[output_path],
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        missing_paths=missing_paths,
    )


def run_bangers(args: argparse.Namespace) -> int:
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")

    input_path = banger_inputs_path(args)
    if not input_path.exists():
        raise SystemExit(
            f"banger input not found: {input_path}; run "
            "scripts/build_suggestion_inputs.py after bridges"
        )

    template = load_template(args.template, ("{combined_json_element}",))
    elements = load_combined_json(input_path)
    selected = select_banger_input_elements(
        elements,
        banger_input_indexes_arg(args),
        args.start,
        args.limit,
    )
    if not selected:
        print("no banger inputs selected", file=sys.stderr)
        return 0

    print(f"banger input path: {input_path}", file=sys.stderr)
    print(f"selected banger inputs: {len(selected)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    print(f"jobs: {args.jobs}", file=sys.stderr)
    print(f"banger batch size: {args.banger_batch_size}", file=sys.stderr)

    batches = banger_batches(selected, args.banger_batch_size)
    selected_to_run: list[list[tuple[int, dict[str, Any]]]] = []
    for batch in batches:
        input_indexes = [input_index for input_index, _ in batch]
        output_path = bangers_batch_path(args, input_indexes)
        if output_path.exists() and not args.force:
            label = f"{input_indexes[0]}-{input_indexes[-1]}"
            print(f"skip banger inputs {label}: {output_path} exists", file=sys.stderr)
            continue
        selected_to_run.append(batch)

    if args.dry_run:
        for batch in selected_to_run:
            print_bangers_batch_dry_run(args, template, batch)
        return 0

    if not selected_to_run:
        return 0

    args.bangers_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_index = {
            executor.submit(
                run_bangers_batch_once,
                args,
                template,
                batch,
            ): [input_index for input_index, _ in batch]
            for batch in selected_to_run
        }
        for future in as_completed(future_to_index):
            input_indexes = future_to_index[future]
            label = (
                str(input_indexes[0])
                if len(input_indexes) == 1
                else f"{input_indexes[0]}-{input_indexes[-1]}"
            )
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                print(
                    f"banger inputs {label} failed: {exc}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return 1
                continue

            append_jsonl(args.run_log, result.record)
            if result.returncode != 0:
                failures += 1
                print(
                    f"banger inputs {label} failed "
                    f"with exit code {result.returncode}; see {result.stderr_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return result.returncode

            if result.missing_paths:
                failures += 1
                missing = ", ".join(str(path) for path in result.missing_paths)
                print(
                    f"banger inputs {label} completed but did not create: "
                    f"{missing}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return 1

    return 1 if failures else 0


def questions_path(args: argparse.Namespace, suggestion: dict[str, Any]) -> Path:
    return args.questions_dir / f"question_{suggestion['_question_id']}.json"


def agent_questions_path(agent_workdir: Path, suggestion: dict[str, Any]) -> Path:
    return agent_workdir / "agent-output" / f"question_{suggestion['_question_id']}.json"


def question_context_for_suggestion(
    indexed_events: list[dict[str, Any]],
    suggestion: dict[str, Any],
) -> list[dict[str, Any]]:
    return context_events_for_timestamp(
        indexed_events,
        suggestion.get("timestamp"),
        QUESTION_CONTEXT_EVENT_COUNT,
    )


def suggestion_title(suggestion: dict[str, Any]) -> str:
    for key in ("title", "suggestion", "action", "expected_artifact", "goal"):
        value = suggestion.get(key)
        if isinstance(value, str) and value:
            return value
    return str(suggestion.get("_question_id", ""))


def attach_question_context(
    data: dict[str, Any],
    suggestion: dict[str, Any],
    context_events: list[dict[str, Any]],
) -> dict[str, Any]:
    output = dict(data)
    output["suggestion_title"] = (
        output.get("suggestion_title")
        if isinstance(output.get("suggestion_title"), str)
        and output.get("suggestion_title")
        else suggestion_title(suggestion)
    )
    output["banger_timestamp"] = suggestion.get("timestamp")
    output["context_events"] = context_events
    return output


def write_json_atomically(path: Path, data: Any) -> None:
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    try:
        tmp.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def normalize_questions_file(
    path: Path,
    suggestion: dict[str, Any],
    context_events: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"questions output is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"questions output must be a JSON object: {path}")

    normalized = attach_question_context(data, suggestion, context_events)
    validate_questions_data(normalized, path)
    if normalized != data:
        write_json_atomically(path, normalized)
    return normalized


def banger_files(bangers_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for pattern in ("bangers_*.json", "banger_*.json")
            for path in bangers_dir.glob(pattern)
        ]
    )


def load_suggestions_from_bangers(args: argparse.Namespace) -> list[dict[str, Any]]:
    if not args.bangers_dir.exists():
        raise SystemExit(f"bangers directory not found: {args.bangers_dir}")

    parsed_indexes = parse_interval_indexes(banger_input_indexes_arg(args))
    suggestions: list[dict[str, Any]] = []
    for path in banger_files(args.bangers_dir):
        for combined_index, data in split_bangers_batch_json(path):
            if parsed_indexes is not None and combined_index not in parsed_indexes:
                continue
            goals = data.get("goals")
            if not isinstance(goals, list):
                raise RuntimeError(f"bangers input goals must be an array: {path}")
            for goal_index, goal in enumerate(goals):
                if not isinstance(goal, dict):
                    continue
                opportunities = goal.get("opportunities")
                if not isinstance(opportunities, list):
                    continue
                for opportunity_index, opportunity in enumerate(opportunities):
                    if not isinstance(opportunity, dict):
                        continue
                    suggestion = dict(opportunity)
                    suggestion["goal"] = goal.get("goal")
                    suggestion["_source_bangers_path"] = str(path)
                    suggestion["_combined_index"] = combined_index
                    suggestion["_goal_index"] = goal_index
                    suggestion["_opportunity_index"] = opportunity_index
                    suggestion["_question_id"] = (
                        f"{combined_index}_{goal_index}_{opportunity_index}"
                    )
                    suggestions.append(suggestion)

    selected = suggestions[args.start:]
    if args.limit is not None:
        selected = selected[: args.limit]
    return selected


def print_questions_dry_run(
    args: argparse.Namespace,
    template: str,
    suggestion: dict[str, Any],
    indexed_events: list[dict[str, Any]],
) -> None:
    output_path = questions_path(args, suggestion)
    context_events = question_context_for_suggestion(indexed_events, suggestion)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(
            args,
            f"questions-{suggestion['_question_id']}",
        )
        isolated_workdir = agent_workdir
        agent_output_path = agent_questions_path(agent_workdir, suggestion)

    provider = build_provider_command(args, agent_workdir)
    prompt = render_questions_prompt(
        template,
        suggestion,
        context_events,
        agent_output_path,
        provider.name,
    )
    print(f"\n--- suggestion {suggestion['_question_id']} ---")
    print(f"bangers path: {suggestion['_source_bangers_path']}")
    print(f"questions path: {output_path}")
    print(f"context events: {len(context_events)}")
    print(f"agent questions path: {agent_output_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def run_questions_once(
    args: argparse.Namespace,
    template: str,
    suggestion: dict[str, Any],
    indexed_events: list[dict[str, Any]],
) -> QuestionsResult:
    suggestion_index = suggestion["_question_id"]
    output_path = questions_path(args, suggestion)
    context_events = question_context_for_suggestion(indexed_events, suggestion)
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_output_path = output_path
    else:
        agent_workdir = create_isolated_workdir(args, f"questions-{suggestion_index}")
        isolated_workdir = agent_workdir
        agent_output_path = agent_questions_path(agent_workdir, suggestion)

    stdout_path = args.questions_dir / (
        f"question_{suggestion_index}.{args.provider}.stdout.log"
    )
    stderr_path = args.questions_dir / (
        f"question_{suggestion_index}.{args.provider}.stderr.log"
    )
    prompt = render_questions_prompt(
        template,
        suggestion,
        context_events,
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
        prefix=f"{args.provider}:questions:{suggestion_index}",
        log_message=f"questions suggestion {suggestion_index} -> {output_path}",
        output_path=output_path,
        agent_output_path=agent_output_path,
    )

    if job.returncode == 0 and output_path.exists():
        normalize_questions_file(output_path, suggestion, context_events)

    record = {
        "provider": job.provider.name,
        "mode": "questions",
        "discovery_dir": str(args.discovery_dir),
        "goals_dir": str(args.goals_dir),
        "combined_dir": str(args.combined_dir),
        "bangers_dir": str(args.bangers_dir),
        "suggestion_index": suggestion_index,
        "combined_index": suggestion["_combined_index"],
        "goal_index": suggestion["_goal_index"],
        "opportunity_index": suggestion["_opportunity_index"],
        "question_context_event_count": len(context_events),
        "questions_path": str(output_path),
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
    return QuestionsResult(
        suggestion_index=suggestion_index,
        record=record,
        questions_path=output_path,
        stderr_path=job.stderr_path,
        returncode=job.returncode,
        created_questions=job.created_output,
    )


def write_final_questions(
    args: argparse.Namespace,
    suggestions: list[dict[str, Any]],
    indexed_events: list[dict[str, Any]],
) -> None:
    final_items: list[dict[str, Any]] = []
    for suggestion in suggestions:
        path = questions_path(args, suggestion)
        if not path.exists():
            continue
        context_events = question_context_for_suggestion(indexed_events, suggestion)
        data = normalize_questions_file(path, suggestion, context_events)
        final_items.append(
            {
                "question_id": suggestion["_question_id"],
                "combined_index": suggestion["_combined_index"],
                "goal_index": suggestion["_goal_index"],
                "opportunity_index": suggestion["_opportunity_index"],
                "banger_timestamp": data.get("banger_timestamp"),
                "context_events": data.get("context_events"),
                "suggestion": suggestion,
                "questions": data,
            }
        )

    final_path = args.questions_dir / "final_questions.json"
    tmp = final_path.with_name(f".{final_path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(final_items, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, final_path)
    print(f"wrote final questions -> {final_path}", file=sys.stderr)


def run_questions(args: argparse.Namespace) -> int:
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")

    template = load_template(args.template, ("{suggestion_json}", "{context_events_json}"))
    selected = load_suggestions_from_bangers(args)
    if not selected:
        print("no banger opportunities selected", file=sys.stderr)
        return 0
    indexed_events = load_indexed_events(args.repo_root / "logs-indexed")
    if not indexed_events:
        raise SystemExit(f"no timestamped events found in {args.repo_root / 'logs-indexed'}")

    print(f"selected banger opportunities: {len(selected)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    print(f"jobs: {args.jobs}", file=sys.stderr)
    print(
        f"question context events per suggestion: {QUESTION_CONTEXT_EVENT_COUNT}",
        file=sys.stderr,
    )

    selected_to_run: list[dict[str, Any]] = []
    for suggestion in selected:
        output_path = questions_path(args, suggestion)
        if output_path.exists() and not args.force:
            context_events = question_context_for_suggestion(indexed_events, suggestion)
            if not args.dry_run:
                normalize_questions_file(output_path, suggestion, context_events)
            print(
                f"skip suggestion {suggestion['_question_id']}: {output_path} exists",
                file=sys.stderr,
            )
            continue
        if args.dry_run:
            print_questions_dry_run(args, template, suggestion, indexed_events)
        else:
            selected_to_run.append(suggestion)

    if args.dry_run:
        return 0
    if not selected_to_run:
        write_final_questions(args, selected, indexed_events)
        return 0

    args.questions_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_index = {
            executor.submit(
                run_questions_once,
                args,
                template,
                suggestion,
                indexed_events,
            ): suggestion["_question_id"]
            for suggestion in selected_to_run
        }
        for future in as_completed(future_to_index):
            suggestion_index = future_to_index[future]
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                print(
                    f"suggestion {suggestion_index} questions failed: {exc}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return 1
                continue

            append_jsonl(args.run_log, result.record)
            if result.returncode != 0:
                failures += 1
                print(
                    f"suggestion {result.suggestion_index} questions failed "
                    f"with exit code {result.returncode}; see {result.stderr_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return result.returncode

            if not result.created_questions:
                failures += 1
                print(
                    f"suggestion {result.suggestion_index} completed but did "
                    f"not create {result.questions_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return 1

    if failures:
        return 1
    write_final_questions(args, selected, indexed_events)
    return 0


def run_discovery(args: argparse.Namespace) -> int:
    if not args.intervals.exists():
        raise SystemExit(f"interval JSONL not found: {args.intervals}")
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")

    template = load_template(args.template, ("{candidate_row}",))
    rows = select_rows(read_jsonl(args.intervals), args.interval_indexes, args.start, args.limit)
    if not rows:
        print("no rows selected", file=sys.stderr)
        return 0
    validate_unique_interval_indexes(rows)

    args.goals_dir.mkdir(parents=True, exist_ok=True)
    print(f"selected rows: {len(rows)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    print(f"jobs: {args.jobs}", file=sys.stderr)
    if not args.no_isolate_agent_workdir:
        print(
            "agent isolation: enabled; child workdirs contain only logs-indexed "
            "and an empty agent-output directory for this stage",
            file=sys.stderr,
        )

    rows_to_run: list[dict[str, Any]] = []
    for row in rows:
        interval_index = int(row["interval_index"])
        goal_path = args.goals_dir / f"goal_{interval_index}.json"
        if goal_path.exists() and not args.force:
            print(f"skip interval {interval_index}: {goal_path} exists", file=sys.stderr)
            continue
        if args.dry_run:
            print_dry_run(args, template, row)
        else:
            rows_to_run.append(row)

    if args.dry_run or not rows_to_run:
        return 0

    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_index = {
            executor.submit(run_one_interval, args, template, row): int(row["interval_index"])
            for row in rows_to_run
        }
        for future in as_completed(future_to_index):
            interval_index = future_to_index[future]
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                print(f"interval {interval_index} failed: {exc}", file=sys.stderr)
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return 1
                continue

            append_jsonl(args.run_log, result.record)
            if result.returncode != 0:
                failures += 1
                print(
                    f"interval {result.interval_index} failed with exit code "
                    f"{result.returncode}; see {result.stderr_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return result.returncode

            if not result.created_goal:
                failures += 1
                print(
                    f"interval {result.interval_index} completed but did not create "
                    f"{result.goal_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return 1

    return 1 if failures else 0


def run(args: argparse.Namespace) -> int:
    if args.questions:
        return run_questions(args)
    if args.bangers:
        return run_bangers(args)
    if args.bridges:
        return run_bridges(args)
    if args.combine:
        return run_combine(args)
    return run_discovery(args)
