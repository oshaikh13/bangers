from __future__ import annotations

import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .process import run_command
from .providers import ProviderCommand, build_provider_command


@dataclass(frozen=True)
class AgentJobResult:
    provider: ProviderCommand
    stdout_path: Path
    stderr_path: Path
    returncode: int
    started_at: str
    completed_at: str
    created_output: bool


def cleanup_isolated_workdir(args, workdir: Path) -> None:
    if args.keep_agent_workdirs:
        print(f"kept isolated agent workdir: {workdir}", file=sys.stderr)
        return
    shutil.rmtree(workdir)


def copy_file_atomically(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{dst.name}.tmp.{os.getpid()}.{uuid.uuid4().hex}")
    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    finally:
        if tmp.exists():
            tmp.unlink()


def run_agent_job(
    args,
    *,
    agent_workdir: Path,
    isolated_workdir: Path | None,
    prompt: str,
    stdout_path: Path,
    stderr_path: Path,
    prefix: str,
    log_message: str,
    output_path: Path | None = None,
    agent_output_path: Path | None = None,
) -> AgentJobResult:
    provider = build_provider_command(args, agent_workdir)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    if agent_output_path is not None:
        agent_output_path.parent.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    print(log_message, file=sys.stderr)
    print(f"{provider.name} command:", " ".join(provider.command), file=sys.stderr)
    try:
        returncode = run_command(
            provider.command,
            agent_workdir,
            prompt,
            stdout_path,
            stderr_path,
            prefix,
        )
        if (
            output_path is not None
            and agent_output_path is not None
            and agent_output_path.exists()
            and agent_output_path != output_path
        ):
            copy_file_atomically(agent_output_path, output_path)
    finally:
        if isolated_workdir is not None:
            cleanup_isolated_workdir(args, isolated_workdir)

    completed_at = datetime.now(timezone.utc).isoformat()
    return AgentJobResult(
        provider=provider,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        returncode=returncode,
        started_at=started_at,
        completed_at=completed_at,
        created_output=output_path.exists() if output_path is not None else False,
    )
