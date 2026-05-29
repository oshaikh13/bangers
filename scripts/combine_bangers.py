#!/usr/bin/env python3
"""Flatten banger opportunity batch files into a timestamp-sorted Markdown list."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISCOVERY_DIR = REPO_ROOT / "discovery_codex_15m"
TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Combine discovery bangers_*.json files into a Markdown list sorted "
            "by opportunity timestamp."
        )
    )
    parser.add_argument(
        "--bangers-dir",
        type=Path,
        help=(
            "Directory containing bangers_*.json files. Defaults to "
            "<discovery-dir>/03_bangers."
        ),
    )
    parser.add_argument(
        "--discovery-dir",
        type=Path,
        default=DEFAULT_DISCOVERY_DIR,
        help="Discovery run directory used when --bangers-dir is omitted.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Markdown output path. Defaults to sequential_bangers.md in the bangers directory.",
    )
    return parser.parse_args()


def banger_files(bangers_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for pattern in ("bangers_*.json", "banger_*.json")
            for path in bangers_dir.glob(pattern)
        ]
    )


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return data


def iter_banger_items(path: Path) -> list[tuple[int, dict[str, Any]]]:
    data = load_json_object(path)
    if "bangers" not in data:
        try:
            combined_index = int(path.stem.removeprefix("banger_"))
        except ValueError as exc:
            raise RuntimeError(
                f"legacy banger file is missing numeric index: {path}"
            ) from exc
        return [(combined_index, data)]

    bangers = data.get("bangers")
    if not isinstance(bangers, list):
        raise RuntimeError(f"expected bangers array in {path}")
    items: list[tuple[int, dict[str, Any]]] = []
    for index, item in enumerate(bangers):
        if not isinstance(item, dict):
            raise RuntimeError(f"expected bangers[{index}] object in {path}")
        input_index = item.get("input_index")
        if not isinstance(input_index, int):
            raise RuntimeError(
                f"expected bangers[{index}].input_index integer in {path}"
            )
        items.append((input_index, item))
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


def load_opportunities(bangers_dir: Path) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []
    for path in banger_files(bangers_dir):
        for combined_index, data in iter_banger_items(path):
            goals = data.get("goals")
            if not isinstance(goals, list):
                raise RuntimeError(f"expected goals array in {path}")

            for goal_index, goal in enumerate(goals):
                if not isinstance(goal, dict):
                    continue
                goal_name = goal.get("goal")
                goal_opportunities = goal.get("opportunities")
                if not isinstance(goal_opportunities, list):
                    continue

                for opportunity_index, opportunity in enumerate(goal_opportunities):
                    if not isinstance(opportunity, dict):
                        continue
                    parsed = parse_timestamp(opportunity.get("timestamp"))
                    opportunities.append(
                        {
                            "sequence_index": 0,
                            "timestamp": opportunity.get("timestamp"),
                            "sort_timestamp": parsed,
                            "display_timestamp": format_timestamp(parsed),
                            "goal": goal_name,
                            "title": opportunity.get("title"),
                            "suggestion": opportunity.get("suggestion"),
                            "why_now": opportunity.get("why_now"),
                            "action": opportunity.get("action"),
                            "expected_artifact": opportunity.get("expected_artifact"),
                            "trigger_evidence": opportunity.get("trigger_evidence", []),
                            "source": {
                                "bangers_path": str(path),
                                "combined_index": combined_index,
                                "goal_index": goal_index,
                                "opportunity_index": opportunity_index,
                                "opportunity_id": (
                                    f"{combined_index}_{goal_index}_{opportunity_index}"
                                ),
                            },
                        }
                    )
    opportunities.sort(
        key=lambda item: (
            item["sort_timestamp"] is None,
            item["sort_timestamp"] or datetime.max.replace(tzinfo=timezone.utc),
            item["source"]["combined_index"],
            item["source"]["goal_index"],
            item["source"]["opportunity_index"],
        )
    )
    for index, opportunity in enumerate(opportunities, start=1):
        opportunity["sequence_index"] = index
    return opportunities


def format_timestamp(timestamp: datetime | None) -> str:
    if timestamp is None:
        return "Missing timestamp"
    local = timestamp.astimezone()
    weekday = local.strftime("%a")
    month = local.strftime("%b")
    hour = local.strftime("%I").lstrip("0") or "0"
    return f"{weekday} {month} {local.day}, {hour}:{local:%M %p}"


def write_text_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def render_markdown(opportunities: list[dict[str, Any]]) -> str:
    lines = ["# Sequential Bangers", ""]
    for item in opportunities:
        title = item["title"] or "Untitled"
        source = item["source"]["opportunity_id"]
        evidence = item.get("trigger_evidence")
        lines.extend(
            [
                f"## {item['sequence_index']}. {item['display_timestamp']} - {title}",
                "",
                f"- Source: `{source}`",
                f"- Goal: {item['goal'] or ''}",
                f"- Suggestion: {item['suggestion'] or ''}",
                f"- Why now: {item['why_now'] or ''}",
                f"- Action: {item['action'] or ''}",
                f"- Expected artifact: {item['expected_artifact'] or ''}",
                "",
            ]
        )
        if isinstance(evidence, list) and evidence:
            lines.extend(["Evidence:", ""])
            for entry in evidence:
                lines.append(f"- {entry}")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    bangers_dir = (args.bangers_dir or args.discovery_dir / "03_bangers").resolve()
    if not bangers_dir.exists():
        raise SystemExit(f"bangers directory not found: {bangers_dir}")

    output = (args.output or bangers_dir / "sequential_bangers.md").resolve()

    opportunities = load_opportunities(bangers_dir)
    write_text_atomically(output, render_markdown(opportunities) + "\n")
    missing = sum(1 for item in opportunities if item["sort_timestamp"] is None)
    print(
        f"wrote {len(opportunities)} opportunities -> {output}"
        + (f" ({missing} missing/unparseable timestamps)" if missing else ""),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
