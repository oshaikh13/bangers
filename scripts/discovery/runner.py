from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .intervals import select_rows
from .io import append_jsonl, read_jsonl
from .process import run_command
from .prompts import load_template, render_prompt
from .providers import build_provider_command


def copy_logs_indexed(src: Path, dst: Path) -> None:
    if not src.exists():
        raise SystemExit(f"logs-indexed not found: {src}")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git"))


def create_isolated_workdir(args: argparse.Namespace, interval_index: int) -> Path:
    workdir = Path(
        tempfile.mkdtemp(prefix=f"discovery-{args.provider}-{interval_index}-")
    ).resolve()
    copy_logs_indexed(args.repo_root / "logs-indexed", workdir / "logs-indexed")
    (workdir / "agent-output").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    return workdir


def cleanup_isolated_workdir(args: argparse.Namespace, workdir: Path) -> None:
    if args.keep_agent_workdirs:
        print(f"kept isolated agent workdir: {workdir}", file=sys.stderr)
        return
    shutil.rmtree(workdir)


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

    args.candidates_dir.mkdir(parents=True, exist_ok=True)
    print(f"selected rows: {len(rows)}", file=sys.stderr)
    print(f"provider: {args.provider}", file=sys.stderr)
    if not args.no_isolate_agent_workdir:
        print(
            "agent isolation: enabled; child workdirs contain only logs-indexed "
            "and an empty agent-output directory",
            file=sys.stderr,
        )

    failures = 0
    for row in rows:
        interval_index = int(row["interval_index"])
        candidate_path = args.candidates_dir / f"candidate_{interval_index}.json"
        if candidate_path.exists() and not args.force:
            print(f"skip interval {interval_index}: {candidate_path} exists", file=sys.stderr)
            continue

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
        if args.dry_run:
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
            continue

        stdout_path = args.candidates_dir / f"candidate_{interval_index}.stdout.log"
        stderr_path = args.candidates_dir / f"candidate_{interval_index}.stderr.log"
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
                shutil.copy2(agent_candidate_path, candidate_path)
        finally:
            if isolated_workdir is not None:
                cleanup_isolated_workdir(args, isolated_workdir)
        completed_at = datetime.now(timezone.utc).isoformat()

        append_jsonl(
            args.run_log,
            {
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
            },
        )

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
