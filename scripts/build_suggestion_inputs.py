#!/usr/bin/env python3
"""Build normalized banger inputs from combined goals and bridge goals."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from discovery.scoping import latest_run_id, run_root_for, scope_slug, update_run_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISCOVERY_DIR = REPO_ROOT / "discovery_codex_15m"
TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Normalize siloed combined goals and bridge goals into banger inputs."
    )
    parser.add_argument(
        "--discovery-dir",
        type=Path,
        default=DEFAULT_DISCOVERY_DIR,
        help="Discovery run directory. Defaults to discovery_codex_15m.",
    )
    parser.add_argument(
        "--combined",
        type=Path,
        help=(
            "Path to combined.json. Defaults to <run-root>/02_goals/combined/combined.json."
        ),
    )
    parser.add_argument(
        "--bridges",
        type=Path,
        help=(
            "Path to bridges.json. Defaults to <run-root>/02_goals/bridges/bridges.json."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path. Defaults to <run-root>/03_bangers/inputs.json.",
    )
    parser.add_argument(
        "--interval-range",
        required=True,
        help="Inclusive interval range for run lookup, e.g. `2-42`.",
    )
    parser.add_argument(
        "--run-id",
        help="Run id. Defaults to latest run for the interval range.",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        help="Explicit run root. Overrides --run-id path derivation.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Accepted for runner consistency; this script always rewrites output.",
    )
    return parser.parse_args()


def load_json_array(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, list):
        raise SystemExit(f"expected JSON array in {path}")

    items: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise SystemExit(f"expected object at {path}[{index}]")
        items.append(item)
    return items


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    match = TIMESTAMP_RE.search(value)
    if not match:
        return None
    timestamp = match.group(0)
    if timestamp.endswith("Z"):
        timestamp = f"{timestamp[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def source_goal_timestamps(item: dict[str, Any]) -> list[datetime]:
    goals = item.get("goals")
    if not isinstance(goals, list):
        return []

    timestamps: list[datetime] = []
    for goal in goals:
        if not isinstance(goal, dict):
            continue
        timestamp = parse_timestamp(goal.get("time"))
        if timestamp is not None:
            timestamps.append(timestamp)
    return timestamps


def time_bounds(timestamps: list[datetime]) -> dict[str, str | None]:
    if not timestamps:
        return {"time": None}
    return {"time": format_timestamp(min(timestamps))}


def numeric_scores(items: list[dict[str, Any]], key: str) -> list[int | float]:
    scores: list[int | float] = []
    for item in items:
        value = item.get(key)
        if isinstance(value, (int, float)):
            scores.append(value)
    return scores


def aggregate_score_fields(items: list[dict[str, Any]]) -> dict[str, int | float | None]:
    output: dict[str, int | float | None] = {}
    for key in ("usefulness", "confidence", "disregard"):
        scores = numeric_scores(items, key)
        if scores:
            output[key] = max(scores)
    return output


def required_string(item: dict[str, Any], key: str, label: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"{label} is missing string field '{key}'")
    return value


def build_goal_input(index: int, item: dict[str, Any]) -> dict[str, Any]:
    label = f"combined goal {index}"
    combined = required_string(item, "combined", label)
    goals = item.get("goals")
    if not isinstance(goals, list):
        raise SystemExit(f"{label} is missing array field 'goals'")

    timestamps = source_goal_timestamps(item)
    score_fields = aggregate_score_fields([goal for goal in goals if isinstance(goal, dict)])
    return {
        "type": "goal",
        "name": combined,
        **time_bounds(timestamps),
        "usefulness": score_fields.get("usefulness"),
        "confidence": score_fields.get("confidence"),
        "disregard": score_fields.get("disregard"),
        "context": required_string(item, "context", label),
        "reasoning": required_string(item, "reasoning", label),
        "description": required_string(item, "description", label),
    }


def build_bridge_input(
    index: int,
    item: dict[str, Any],
    combined: list[dict[str, Any]],
) -> dict[str, Any]:
    label = f"bridge {index}"
    bridge = required_string(item, "bridge", label)
    connected_goals = item.get("connected_goals")
    if not isinstance(connected_goals, list) or len(connected_goals) < 2:
        raise SystemExit(f"{label} must include at least two connected_goals")

    return {
        "type": "bridge",
        "name": bridge,
        **bridge_time_bounds(item, combined),
        "usefulness": item.get("usefulness"),
        "confidence": item.get("confidence"),
        "disregard": item.get("disregard"),
        "context": required_string(item, "context", label),
        "reasoning": required_string(item, "reasoning", label),
        "description": required_string(item, "description", label),
    }


def bridge_time_bounds(
    bridge: dict[str, Any],
    combined: list[dict[str, Any]],
) -> dict[str, str | None]:
    connected_goals = bridge.get("connected_goals")
    if not isinstance(connected_goals, list):
        return {"time": None}

    connected_earliest: list[datetime] = []
    all_timestamps: list[datetime] = []
    for connected in connected_goals:
        if not isinstance(connected, dict):
            continue
        combined_index = connected.get("combined_index")
        if not isinstance(combined_index, int):
            continue
        if combined_index < 0 or combined_index >= len(combined):
            continue
        timestamps = source_goal_timestamps(combined[combined_index])
        if not timestamps:
            continue
        connected_earliest.append(min(timestamps))
        all_timestamps.extend(timestamps)

    if not all_timestamps:
        best_timing = parse_timestamp(bridge.get("best_timing"))
        return {"time": format_timestamp(best_timing)}

    # A bridge becomes knowable once every connected goal has at least appeared.
    created_at = max(connected_earliest) if connected_earliest else min(all_timestamps)
    return {"time": format_timestamp(created_at)}


def sort_key(item: dict[str, Any]) -> tuple[bool, str, int]:
    created_at = item.get("time")
    type_order = 0 if item.get("type") == "goal" else 1
    if not isinstance(created_at, str):
        return (True, "", type_order)
    return (False, created_at, type_order)


def write_json_atomically(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    args = parse_args()
    discovery_dir = args.discovery_dir.resolve()
    slug = scope_slug(args)
    if args.run_root:
        run_root = args.run_root.resolve()
        args.run_id = args.run_id or run_root.name
    else:
        run_id = args.run_id or latest_run_id(discovery_dir, slug)
        args.run_id = run_id
        run_root = run_root_for(discovery_dir, slug, run_id).resolve()
    args.run_root = run_root
    combined_path = (
        args.combined
        or run_root / "02_goals" / "combined" / "combined.json"
    ).resolve()
    bridges_path = (
        args.bridges
        or run_root / "02_goals" / "bridges" / "bridges.json"
    ).resolve()
    output_path = (
        args.output
        or run_root / "03_bangers" / "inputs.json"
    ).resolve()

    if not combined_path.exists():
        raise SystemExit(f"combined goals not found: {combined_path}")
    if not bridges_path.exists():
        raise SystemExit(f"bridge goals not found: {bridges_path}")

    combined = load_json_array(combined_path)
    bridges = load_json_array(bridges_path)
    inputs = [
        *(build_goal_input(index, item) for index, item in enumerate(combined)),
        *(build_bridge_input(index, item, combined) for index, item in enumerate(bridges)),
    ]
    inputs = sorted(inputs, key=sort_key)

    write_json_atomically(output_path, inputs)
    update_run_manifest(args, "03_bangers:inputs")
    print(
        f"wrote {len(inputs)} suggestion inputs "
        f"({len(combined)} goals, {len(bridges)} bridges) -> {output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
