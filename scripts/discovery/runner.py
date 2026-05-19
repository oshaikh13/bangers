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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tqdm import tqdm

from .intervals import parse_interval_indexes, select_rows
from .io import append_jsonl, read_jsonl
from .process import run_command
from .prompts import (
    load_template,
    render_combine_prompt,
    render_discovery_prompt,
    render_questions_prompt,
)
from .providers import build_provider_command

SCREENSHOTS_DIR = "screenshots"


@dataclass(frozen=True)
class IntervalResult:
    interval_index: int
    record: dict[str, Any]
    candidate_path: Path
    stderr_path: Path
    returncode: int
    created_candidate: bool


@dataclass(frozen=True)
class CombineResult:
    record: dict[str, Any]
    combined_path: Path
    stderr_path: Path
    returncode: int
    created_combined: bool


@dataclass(frozen=True)
class QuestionsResult:
    combined_index: int
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
    interval_index: int,
    progress_every: int,
) -> None:
    total = count_files(src)
    dst.mkdir(parents=True, exist_ok=True)
    miniters = progress_every or None
    files = iter_files(src)
    for src_file, rel_path in tqdm(
        files,
        total=total,
        desc=f"startup interval {interval_index}",
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


def symlink_screenshot_tree(src: Path, dst: Path, interval_index: int) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(src, dst, target_is_directory=True)
    except OSError as exc:
        raise RuntimeError(
            f"failed to symlink screenshots into isolated discovery workdir: "
            f"{src} -> {dst}: {exc}"
        ) from exc
    tqdm.write(
        f"startup interval {interval_index}: symlinked screenshots directory",
        file=sys.stderr,
    )


def copy_logs_indexed(src: Path, dst: Path, args: argparse.Namespace,
                      interval_index: int) -> None:
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
            symlink_screenshot_tree(src_screenshots, dst_screenshots, interval_index)
        else:
            hardlink_screenshot_tree(
                src_screenshots,
                dst_screenshots,
                interval_index,
                args.startup_progress_every,
            )


def create_isolated_workdir(args: argparse.Namespace, interval_index: int) -> Path:
    workdir = Path(
        tempfile.mkdtemp(prefix=f"discovery-{args.provider}-{interval_index}-")
    ).resolve()
    copy_logs_indexed(
        args.repo_root / "logs-indexed",
        workdir / "logs-indexed",
        args,
        interval_index,
    )
    (workdir / "agent-output").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    return workdir


def cleanup_isolated_workdir(args: argparse.Namespace, workdir: Path) -> None:
    if args.keep_agent_workdirs:
        print(f"kept isolated agent workdir: {workdir}", file=sys.stderr)
        return
    shutil.rmtree(workdir)


def copy_candidate_atomically(src: Path, dst: Path) -> None:
    tmp = dst.with_name(f".{dst.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def run_one_interval(
    args: argparse.Namespace,
    template: str,
    row: dict[str, Any],
) -> IntervalResult:
    interval_index = int(row["interval_index"])
    candidate_path = args.candidates_dir / f"candidate_{interval_index}.json"
    stdout_path = args.candidates_dir / f"candidate_{interval_index}.stdout.log"
    stderr_path = args.candidates_dir / f"candidate_{interval_index}.stderr.log"

    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_candidate_path = candidate_path
    else:
        agent_workdir = create_isolated_workdir(args, interval_index)
        isolated_workdir = agent_workdir
        agent_candidate_path = (
            agent_workdir / "agent-output" / f"candidate_{interval_index}.json"
        )

    provider = build_provider_command(args, agent_workdir)
    prompt = render_discovery_prompt(template, row, agent_candidate_path, provider.name)
    started_at = datetime.now(timezone.utc).isoformat()
    print(f"run interval {interval_index} -> {candidate_path}", file=sys.stderr)
    print(f"{provider.name} command:", " ".join(provider.command), file=sys.stderr)

    try:
        returncode = run_command(
            provider.command,
            agent_workdir,
            prompt,
            stdout_path,
            stderr_path,
            f"{provider.name}:{interval_index}",
        )
        if agent_candidate_path.exists() and agent_candidate_path != candidate_path:
            copy_candidate_atomically(agent_candidate_path, candidate_path)
    finally:
        if isolated_workdir is not None:
            cleanup_isolated_workdir(args, isolated_workdir)

    completed_at = datetime.now(timezone.utc).isoformat()
    record = {
        "provider": provider.name,
        "discovery_kind": args.discovery_kind,
        "interval_index": interval_index,
        "candidate_path": str(candidate_path),
        "agent_candidate_path": str(agent_candidate_path),
        "agent_isolated": not args.no_isolate_agent_workdir,
        "agent_visible_roots": ["logs-indexed"]
        if not args.no_isolate_agent_workdir
        else ["repo_root"],
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "returncode": returncode,
        "started_at": started_at,
        "completed_at": completed_at,
        "model": provider.model,
        "effort": provider.effort,
        "sandbox": provider.sandbox,
    }
    return IntervalResult(
        interval_index=interval_index,
        record=record,
        candidate_path=candidate_path,
        stderr_path=stderr_path,
        returncode=returncode,
        created_candidate=candidate_path.exists(),
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
    candidate_path = args.candidates_dir / f"candidate_{interval_index}.json"
    isolated_workdir: Path | None = None
    if args.no_isolate_agent_workdir:
        agent_workdir = args.repo_root
        agent_candidate_path = candidate_path
    else:
        agent_workdir = create_isolated_workdir(args, interval_index)
        isolated_workdir = agent_workdir
        agent_candidate_path = (
            agent_workdir / "agent-output" / f"candidate_{interval_index}.json"
        )

    provider = build_provider_command(args, agent_workdir)
    prompt = render_discovery_prompt(template, row, agent_candidate_path, provider.name)
    print(f"\n--- interval {interval_index} ---")
    print(f"candidate path: {candidate_path}")
    print(f"agent workdir: {agent_workdir}")
    print(f"agent candidate path: {agent_candidate_path}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
    if isolated_workdir is not None:
        cleanup_isolated_workdir(args, isolated_workdir)


def candidate_files(candidates_dir: Path) -> list[Path]:
    return sorted(candidates_dir.glob("candidate_*.json"))


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


def select_combined_elements(
    elements: list[dict[str, Any]],
    combined_indexes: str | None,
    start: int,
    limit: int | None,
) -> list[tuple[int, dict[str, Any]]]:
    selected = list(enumerate(elements))
    parsed_indexes = parse_interval_indexes(combined_indexes)
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
    if not isinstance(data, dict):
        raise RuntimeError(f"questions output must be a JSON object: {path}")
    if "question_answer_pairs" in data and not isinstance(
        data["question_answer_pairs"], list
    ):
        raise RuntimeError(
            f"questions output question_answer_pairs must be an array: {path}"
        )
    for index, pair in enumerate(data.get("question_answer_pairs", [])):
        if not isinstance(pair, dict):
            raise RuntimeError(
                f"questions output question_answer_pairs[{index}] must be an "
                f"object: {path}"
            )
        if not isinstance(pair.get("time"), str) or not pair["time"]:
            raise RuntimeError(
                f"questions output question_answer_pairs[{index}].time must be "
                f"a non-empty string: {path}"
            )


def print_combine_dry_run(args: argparse.Namespace, template: str) -> None:
    provider = build_provider_command(args, args.repo_root)
    prompt = render_combine_prompt(template, args.candidates_dir, provider.name)
    print("\n--- combine candidates ---")
    print(f"candidates dir: {args.candidates_dir}")
    print(f"combined path: {args.candidates_dir / 'combined.json'}")
    print(f"agent workdir: {args.repo_root}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))


def run_combine_once(args: argparse.Namespace, template: str) -> CombineResult:
    provider = build_provider_command(args, args.repo_root)
    combined_path = args.candidates_dir / "combined.json"
    stdout_path = args.candidates_dir / f"combined.{provider.name}.stdout.log"
    stderr_path = args.candidates_dir / f"combined.{provider.name}.stderr.log"
    prompt = render_combine_prompt(template, args.candidates_dir, provider.name)
    started_at = datetime.now(timezone.utc).isoformat()
    files = candidate_files(args.candidates_dir)

    print(f"combine {len(files)} candidates -> {combined_path}", file=sys.stderr)
    print(f"{provider.name} command:", " ".join(provider.command), file=sys.stderr)
    returncode = run_command(
        provider.command,
        args.repo_root,
        prompt,
        stdout_path,
        stderr_path,
        f"{provider.name}:combine",
    )

    if returncode == 0 and combined_path.exists():
        validate_combined_json(combined_path)

    completed_at = datetime.now(timezone.utc).isoformat()
    record = {
        "provider": provider.name,
        "mode": "combine",
        "discovery_kind": args.discovery_kind,
        "candidates_dir": str(args.candidates_dir),
        "combined_path": str(combined_path),
        "candidate_count": len(files),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "returncode": returncode,
        "started_at": started_at,
        "completed_at": completed_at,
        "model": provider.model,
        "effort": provider.effort,
        "sandbox": provider.sandbox,
    }
    return CombineResult(
        record=record,
        combined_path=combined_path,
        stderr_path=stderr_path,
        returncode=returncode,
        created_combined=combined_path.exists(),
    )


def run_combine(args: argparse.Namespace) -> int:
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")
    if not args.candidates_dir.exists():
        raise SystemExit(f"candidates directory not found: {args.candidates_dir}")
    files = candidate_files(args.candidates_dir)
    if not files:
        raise SystemExit(f"no candidate_*.json files found in {args.candidates_dir}")

    template = load_template(args.template, ("{dir_name}",))
    combined_path = args.candidates_dir / "combined.json"
    if combined_path.exists() and not args.force:
        print(f"skip combine: {combined_path} exists", file=sys.stderr)
        return 0

    print(f"selected candidate files: {len(files)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    print(f"discovery kind: {args.discovery_kind}", file=sys.stderr)
    if args.dry_run:
        print_combine_dry_run(args, template)
        return 0

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


def questions_path(args: argparse.Namespace, combined_index: int) -> Path:
    return args.questions_dir / f"question_{combined_index}.json"


def print_questions_dry_run(
    args: argparse.Namespace,
    template: str,
    combined_index: int,
    combined_element: dict[str, Any],
) -> None:
    provider = build_provider_command(args, args.repo_root)
    output_path = questions_path(args, combined_index)
    prompt = render_questions_prompt(
        template,
        combined_element,
        output_path,
        provider.name,
    )
    print(f"\n--- combined element {combined_index} ---")
    print(f"combined path: {args.candidates_dir / 'combined.json'}")
    print(f"questions path: {output_path}")
    print(f"agent workdir: {args.repo_root}")
    print(f"{provider.name} command:", " ".join(provider.command))
    if args.print_prompt:
        print(prompt)
    else:
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))


def run_questions_once(
    args: argparse.Namespace,
    template: str,
    combined_index: int,
    combined_element: dict[str, Any],
) -> QuestionsResult:
    provider = build_provider_command(args, args.repo_root)
    output_path = questions_path(args, combined_index)
    stdout_path = args.questions_dir / f"question_{combined_index}.{provider.name}.stdout.log"
    stderr_path = args.questions_dir / f"question_{combined_index}.{provider.name}.stderr.log"
    prompt = render_questions_prompt(
        template,
        combined_element,
        output_path,
        provider.name,
    )
    started_at = datetime.now(timezone.utc).isoformat()

    print(f"questions combined {combined_index} -> {output_path}", file=sys.stderr)
    print(f"{provider.name} command:", " ".join(provider.command), file=sys.stderr)
    returncode = run_command(
        provider.command,
        args.repo_root,
        prompt,
        stdout_path,
        stderr_path,
        f"{provider.name}:questions:{combined_index}",
    )

    if returncode == 0 and output_path.exists():
        validate_questions_json(output_path)

    completed_at = datetime.now(timezone.utc).isoformat()
    record = {
        "provider": provider.name,
        "mode": "questions",
        "discovery_kind": args.discovery_kind,
        "candidates_dir": str(args.candidates_dir),
        "combined_path": str(args.candidates_dir / "combined.json"),
        "combined_index": combined_index,
        "questions_path": str(output_path),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "returncode": returncode,
        "started_at": started_at,
        "completed_at": completed_at,
        "model": provider.model,
        "effort": provider.effort,
        "sandbox": provider.sandbox,
    }
    return QuestionsResult(
        combined_index=combined_index,
        record=record,
        questions_path=output_path,
        stderr_path=stderr_path,
        returncode=returncode,
        created_questions=output_path.exists(),
    )


def run_questions(args: argparse.Namespace) -> int:
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")
    if not args.candidates_dir.exists():
        raise SystemExit(f"candidates directory not found: {args.candidates_dir}")

    combined_path = args.candidates_dir / "combined.json"
    if not combined_path.exists():
        raise SystemExit(f"combined.json not found: {combined_path}")

    template = load_template(args.template, ("{combined_json_element}",))
    elements = load_combined_json(combined_path)
    selected = select_combined_elements(
        elements,
        args.combined_indexes,
        args.start,
        args.limit,
    )
    if not selected:
        print("no combined elements selected", file=sys.stderr)
        return 0

    print(f"selected combined elements: {len(selected)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    print(f"discovery kind: {args.discovery_kind}", file=sys.stderr)
    print(f"jobs: {args.jobs}", file=sys.stderr)

    selected_to_run: list[tuple[int, dict[str, Any]]] = []
    for combined_index, combined_element in selected:
        output_path = questions_path(args, combined_index)
        if output_path.exists() and not args.force:
            print(
                f"skip combined element {combined_index}: {output_path} exists",
                file=sys.stderr,
            )
            continue
        if args.dry_run:
            print_questions_dry_run(args, template, combined_index, combined_element)
        else:
            selected_to_run.append((combined_index, combined_element))

    if args.dry_run or not selected_to_run:
        return 0

    args.questions_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        future_to_index = {
            executor.submit(
                run_questions_once,
                args,
                template,
                combined_index,
                combined_element,
            ): combined_index
            for combined_index, combined_element in selected_to_run
        }
        for future in as_completed(future_to_index):
            combined_index = future_to_index[future]
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                print(
                    f"combined element {combined_index} questions failed: {exc}",
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
                    f"combined element {result.combined_index} questions failed "
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
                    f"combined element {result.combined_index} completed but did "
                    f"not create {result.questions_path}",
                    file=sys.stderr,
                )
                if not args.continue_on_error:
                    for pending in future_to_index:
                        pending.cancel()
                    return 1

    return 1 if failures else 0


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

    args.candidates_dir.mkdir(parents=True, exist_ok=True)
    print(f"selected rows: {len(rows)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    print(f"discovery kind: {args.discovery_kind}", file=sys.stderr)
    print(f"jobs: {args.jobs}", file=sys.stderr)
    if not args.no_isolate_agent_workdir:
        print(
            "agent isolation: enabled; child workdirs contain only logs-indexed "
            "and an empty agent-output directory",
            file=sys.stderr,
        )

    rows_to_run: list[dict[str, Any]] = []
    for row in rows:
        interval_index = int(row["interval_index"])
        candidate_path = args.candidates_dir / f"candidate_{interval_index}.json"
        if candidate_path.exists() and not args.force:
            print(f"skip interval {interval_index}: {candidate_path} exists", file=sys.stderr)
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

            if not result.created_candidate:
                failures += 1
                print(
                    f"interval {result.interval_index} completed but did not create "
                    f"{result.candidate_path}",
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
    if args.combine:
        return run_combine(args)
    return run_discovery(args)
