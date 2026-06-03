from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .intervals import parse_interval_range


def interval_range_slug(raw: str) -> str:
    start, end = parse_interval_range(raw) or (None, None)
    if start is None or end is None:
        raise SystemExit("--interval-range is required")
    return f"intervals_{start}-{end}"


def scope_slug(args: Any) -> str:
    interval_range = getattr(args, "interval_range", None)
    if not interval_range:
        raise SystemExit("--interval-range is required")
    return interval_range_slug(interval_range)


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run_root_for(discovery_dir: Path, slug: str, run_id: str) -> Path:
    return discovery_dir / slug / run_id


def latest_run_id(discovery_dir: Path, slug: str) -> str:
    scope_dir = discovery_dir / slug
    if not scope_dir.exists():
        raise SystemExit(f"no runs found for {slug}: {scope_dir}")
    run_ids = sorted(path.name for path in scope_dir.iterdir() if path.is_dir())
    if not run_ids:
        raise SystemExit(f"no runs found for {slug}: {scope_dir}")
    return run_ids[-1]


def write_json_atomically(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def update_run_manifest(
    args: Any,
    stage: str,
    selected_rows: list[dict[str, Any]] | None = None,
    *,
    status: str = "completed",
) -> None:
    run_root = getattr(args, "run_root", None)
    if run_root is None:
        return

    path = Path(run_root) / "manifest.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "interval_range": getattr(args, "interval_range", None),
            "scope_slug": getattr(args, "scope_slug", None),
            "run_id": getattr(args, "run_id", None),
            "provider": getattr(args, "provider", None),
            "interval_minutes": getattr(args, "interval_minutes", None),
            "model": getattr(args, "codex_model", None)
            if getattr(args, "provider", None) == "codex"
            else getattr(args, "claude_model", None),
            "stages": {},
        }

    if selected_rows is not None:
        data["selected_interval_rows"] = selected_rows
    stages = data.setdefault("stages", {})
    stages[stage] = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }
    write_json_atomically(path, data)
