from __future__ import annotations

from pathlib import Path
from typing import Any


def selector_slug(raw: str) -> str:
    return (
        raw.strip()
        .replace(",", "_")
        .replace("-", "-")
        .replace(" ", "")
        or "selected"
    )


def scope_slug(args: Any) -> str:
    days = getattr(args, "days", None)
    if days:
        return f"days_{selector_slug(days)}"

    interval_indexes = getattr(args, "interval_indexes", None)
    if interval_indexes:
        return f"intervals_{selector_slug(interval_indexes)}"

    return "global"


def scoped_stage_dir(discovery_dir: Path, stage_name: str, slug: str) -> Path:
    base = discovery_dir / stage_name
    if slug == "global":
        return base
    return base / slug
