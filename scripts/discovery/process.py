from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from typing import TextIO


def stream_pipe(pipe: TextIO, log_file: TextIO, console: TextIO, prefix: str) -> None:
    try:
        for line in iter(pipe.readline, ""):
            log_file.write(line)
            log_file.flush()
            console.write(f"{prefix}{line}")
            console.flush()
    finally:
        pipe.close()


def run_command(
    command: list[str],
    cwd: Path,
    prompt: str,
    stdout_path: Path,
    stderr_path: Path,
    prefix: str,
) -> int:
    with stdout_path.open("w", encoding="utf-8") as stdout_log, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_log:
        proc = subprocess.Popen(
            command,
            cwd=cwd,
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
            args=(proc.stdout, stdout_log, sys.stdout, f"[{prefix} stdout] "),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=stream_pipe,
            args=(proc.stderr, stderr_log, sys.stderr, f"[{prefix} stderr] "),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()

        proc.stdin.write(prompt)
        proc.stdin.close()
        returncode = proc.wait()
        stdout_thread.join()
        stderr_thread.join()
        return returncode

