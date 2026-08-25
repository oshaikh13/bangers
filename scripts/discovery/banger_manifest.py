from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .runner import split_bangers_batch_json


def banger_files(bangers_dir: Path) -> list[Path]:
    return sorted(
        [
            path
            for pattern in ("bangers_*.json", "banger_*.json")
            for path in bangers_dir.glob(pattern)
        ]
    )


def load_seed_candidates(bangers_dir: Path) -> list[dict[str, Any]]:
    if not bangers_dir.exists():
        raise SystemExit(f"bangers directory not found: {bangers_dir}")

    seeds: list[dict[str, Any]] = []
    for path in banger_files(bangers_dir):
        for combined_index, data in split_bangers_batch_json(path):
            goals = data.get("goals")
            if not isinstance(goals, list):
                continue
            for goal_index, goal in enumerate(goals):
                if not isinstance(goal, dict):
                    continue
                opportunities = goal.get("opportunities")
                if not isinstance(opportunities, list):
                    continue
                for opportunity_index, opportunity in enumerate(opportunities):
                    if not isinstance(opportunity, dict):
                        continue
                    seed_id = f"{combined_index}_{goal_index}_{opportunity_index}"
                    seeds.append(
                        {
                            "seed_id": seed_id,
                            "combined_index": combined_index,
                            "goal_index": goal_index,
                            "opportunity_index": opportunity_index,
                            "banger_timestamp": opportunity.get("timestamp"),
                            "goal": goal.get("goal"),
                            "suggestion": opportunity.get("suggestion"),
                            "action": opportunity.get("action"),
                            "expected_artifact": opportunity.get("expected_artifact"),
                            "usefulness": opportunity.get("usefulness"),
                            "confidence": opportunity.get("confidence"),
                            "surprise": opportunity.get("surprise"),
                            "disregard": opportunity.get("disregard"),
                            "trigger_evidence": opportunity.get("trigger_evidence"),
                            "why_now": opportunity.get("why_now"),
                            "source_bangers_path": str(path),
                            "target_banger": {
                                "goal": goal.get("goal"),
                                **opportunity,
                            },
                        }
                    )
    return seeds


def build_combined_bangers(bangers_dir: Path) -> dict[str, Any]:
    files = banger_files(bangers_dir)
    seeds = load_seed_candidates(bangers_dir)
    return {
        "source_bangers_dir": str(bangers_dir),
        "source_bangers_files": [str(path) for path in files],
        "seed_count": len(seeds),
        "seeds": seeds,
    }


def write_json_atomically(path: Path, data: dict[str, Any]) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_combined_bangers_file(path: Path, bangers_dir: Path) -> dict[str, Any]:
    data = build_combined_bangers(bangers_dir)
    write_json_atomically(path, data)
    return data
