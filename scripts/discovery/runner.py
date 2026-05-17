from __future__ import annotations

import argparse
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

from .intervals import select_rows
from .io import append_jsonl, read_jsonl
from .process import run_command
from .prompts import load_template, render_prompt
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
    prompt = render_prompt(template, row, agent_candidate_path, provider.name)
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
    prompt = render_prompt(template, row, agent_candidate_path, provider.name)
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


def run(args: argparse.Namespace) -> int:
    if not args.intervals.exists():
        raise SystemExit(f"interval JSONL not found: {args.intervals}")
    if not args.repo_root.exists():
        raise SystemExit(f"repo root not found: {args.repo_root}")

    template = load_template(args.template)
    rows = select_rows(read_jsonl(args.intervals), args.interval_indexes, args.start, args.limit)
    if not rows:
        print("no rows selected", file=sys.stderr)
        return 0
    validate_unique_interval_indexes(rows)

    args.candidates_dir.mkdir(parents=True, exist_ok=True)
    print(f"selected rows: {len(rows)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
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
