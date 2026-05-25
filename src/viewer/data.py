from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

GOAL_PATTERN = re.compile(r"^goal_(\d+)\.json$")
BANGER_PATTERN = re.compile(r"^banger_(\d+)\.json$")
QUESTION_PATTERN = re.compile(r"^question_(.+)\.json$")
COMBINED_RELATIVE_PATHS = (
    "02a_combined/combined.json",
    "02_combined/combined.json",
)


def resolve_combined_path(run_path: Path) -> Path | None:
    for relative in COMBINED_RELATIVE_PATHS:
        path = run_path / relative
        if path.is_file():
            return path
    return None


@dataclass(frozen=True)
class RunInfo:
    name: str
    path: Path
    goal_count: int
    has_goals: bool
    has_combined: bool
    has_bangers: bool
    has_questions: bool


def list_discovery_runs(repo_root: Path = REPO_ROOT) -> list[RunInfo]:
    runs: list[RunInfo] = []
    for path in sorted(repo_root.glob("discovery_*")):
        if not path.is_dir():
            continue
        runs.append(describe_run(path))
    runs.sort(key=_run_sort_key, reverse=True)
    return runs


def _run_sort_key(run: RunInfo) -> tuple[int, float]:
    goals_dir = run.path / "01_goals"
    goal_files = [
        path
        for path in goals_dir.glob("goal_*.json")
        if GOAL_PATTERN.match(path.name)
    ]
    latest_mtime = max((path.stat().st_mtime for path in goal_files), default=0.0)
    return (len(goal_files), latest_mtime)


def resolve_run_path(run_name: str, repo_root: Path = REPO_ROOT) -> Path:
    path = (repo_root / run_name).resolve()
    if not path.is_dir() or not path.name.startswith("discovery_"):
        raise FileNotFoundError(f"discovery run not found: {run_name}")
    if repo_root.resolve() not in path.parents:
        raise FileNotFoundError(f"discovery run outside repo root: {run_name}")
    return path


def default_run_name(repo_root: Path = REPO_ROOT) -> str | None:
    runs = list_discovery_runs(repo_root)
    return runs[0].name if runs else None


def describe_run(path: Path) -> RunInfo:
    goals_dir = path / "01_goals"
    bangers_dir = path / "03_bangers"
    questions_dir = path / "04_questions"
    final_questions = questions_dir / "final_questions.json"
    goal_count = 0
    if goals_dir.is_dir():
        try:
            goal_count = len(load_all_goals(path))
        except (ValueError, OSError):
            goal_count = len(list_goal_intervals(path))
    return RunInfo(
        name=path.name,
        path=path,
        goal_count=goal_count,
        has_goals=goal_count > 0,
        has_combined=resolve_combined_path(path) is not None,
        has_bangers=any(bangers_dir.glob("banger_*.json")),
        has_questions=final_questions.is_file() or any(
            questions_dir.glob("question_*.json")
        ),
    )


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def list_goal_intervals(run_path: Path) -> list[dict[str, Any]]:
    goals_dir = run_path / "01_goals"
    intervals: list[dict[str, Any]] = []
    for path in sorted(goals_dir.glob("goal_*.json")):
        match = GOAL_PATTERN.match(path.name)
        if not match:
            continue
        interval = int(match.group(1))
        intervals.append({"interval_index": interval, "path": path.name})
    intervals.sort(key=lambda item: item["interval_index"])
    return intervals


def load_goal(run_path: Path, interval: int) -> list[dict[str, Any]]:
    path = run_path / "01_goals" / f"goal_{interval}.json"
    if not path.is_file():
        raise FileNotFoundError(f"goal file not found: goal_{interval}.json")
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError(f"expected goal array in {path.name}")
    return data


def load_all_goals(run_path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for interval_info in list_goal_intervals(run_path):
        interval = interval_info["interval_index"]
        for rank, goal in enumerate(load_goal(run_path, interval), start=1):
            if not isinstance(goal, dict):
                continue
            items.append(
                {
                    "id": f"{interval}-{rank}",
                    "interval_index": interval,
                    "rank": rank,
                    **goal,
                }
            )
    return items


def load_combined(run_path: Path) -> list[dict[str, Any]]:
    path = resolve_combined_path(run_path)
    if path is None:
        raise FileNotFoundError("combined.json not found")
    data = load_json(path)
    if not isinstance(data, list):
        raise ValueError("expected combined.json to be an array")
    return data


def list_banger_indexes(run_path: Path) -> list[dict[str, Any]]:
    bangers_dir = run_path / "03_bangers"
    indexes: list[dict[str, Any]] = []
    for path in sorted(bangers_dir.glob("banger_*.json")):
        match = BANGER_PATTERN.match(path.name)
        if not match:
            continue
        combined_index = int(match.group(1))
        indexes.append({"combined_index": combined_index, "path": path.name})
    indexes.sort(key=lambda item: item["combined_index"])
    return indexes


def load_banger(run_path: Path, combined_index: int) -> dict[str, Any]:
    path = run_path / "03_bangers" / f"banger_{combined_index}.json"
    if not path.is_file():
        raise FileNotFoundError(f"banger file not found: banger_{combined_index}.json")
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"expected banger object in {path.name}")
    return data


def list_questions(run_path: Path) -> list[dict[str, Any]]:
    final_path = run_path / "04_questions" / "final_questions.json"
    if final_path.is_file():
        data = load_json(final_path)
        if not isinstance(data, list):
            raise ValueError("expected final_questions.json to be an array")
        return [
            {
                "question_id": item.get("question_id"),
                "combined_index": item.get("combined_index"),
                "goal_index": item.get("goal_index"),
                "opportunity_index": item.get("opportunity_index"),
                "suggestion_title": _suggestion_title(item),
            }
            for item in data
            if isinstance(item, dict)
        ]

    questions_dir = run_path / "04_questions"
    items: list[dict[str, Any]] = []
    for path in sorted(questions_dir.glob("question_*.json")):
        match = QUESTION_PATTERN.match(path.name)
        if not match:
            continue
        question_id = match.group(1)
        parts = question_id.split("_")
        combined_index = int(parts[0]) if parts else None
        goal_index = int(parts[1]) if len(parts) > 1 else None
        opportunity_index = int(parts[2]) if len(parts) > 2 else None
        data = load_json(path)
        items.append(
            {
                "question_id": question_id,
                "combined_index": combined_index,
                "goal_index": goal_index,
                "opportunity_index": opportunity_index,
                "suggestion_title": _suggestion_title_from_questions(data),
            }
        )
    return items


def load_question(run_path: Path, question_id: str) -> dict[str, Any]:
    final_path = run_path / "04_questions" / "final_questions.json"
    if final_path.is_file():
        data = load_json(final_path)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("question_id") == question_id:
                    return item

    path = run_path / "04_questions" / f"question_{question_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"question file not found: question_{question_id}.json")
    data = load_json(path)
    parts = question_id.split("_")
    return {
        "question_id": question_id,
        "combined_index": int(parts[0]) if parts else None,
        "goal_index": int(parts[1]) if len(parts) > 1 else None,
        "opportunity_index": int(parts[2]) if len(parts) > 2 else None,
        "questions": data,
    }


def build_manifest(run_path: Path) -> dict[str, Any]:
    run = describe_run(run_path)
    combined = load_combined(run_path) if run.has_combined else []
    bangers = list_banger_indexes(run_path) if run.has_bangers else []
    questions = list_questions(run_path) if run.has_questions else []
    goals = list_goal_intervals(run_path) if run.has_goals else []

    combined_items = [
        {
            "combined_index": index,
            "combined": item.get("combined"),
            "source_goal_count": len(item.get("goals") or []),
            "has_banger": any(
                banger["combined_index"] == index for banger in bangers
            ),
            "question_ids": [
                question["question_id"]
                for question in questions
                if question.get("combined_index") == index
            ],
        }
        for index, item in enumerate(combined)
    ]

    combined_path = resolve_combined_path(run_path)

    return {
        "run": run.name,
        "combined_path": (
            str(combined_path.relative_to(run_path)) if combined_path is not None else None
        ),
        "stages": {
            "goals": run.has_goals,
            "combined": run.has_combined,
            "bangers": run.has_bangers,
            "questions": run.has_questions,
        },
        "counts": {
            "goals": len(goals),
            "combined": len(combined_items),
            "bangers": len(bangers),
            "questions": len(questions),
        },
        "goals": goals,
        "combined": combined_items,
        "bangers": bangers,
        "questions": questions,
    }


def _suggestion_title(item: dict[str, Any]) -> str | None:
    questions = item.get("questions")
    if isinstance(questions, dict):
        title = questions.get("suggestion_title")
        if title:
            return str(title)
    suggestion = item.get("suggestion")
    if isinstance(suggestion, dict):
        for key in ("suggestion", "action", "goal"):
            value = suggestion.get(key)
            if value:
                return str(value)
    return None


def _suggestion_title_from_questions(data: Any) -> str | None:
    if isinstance(data, dict):
        title = data.get("suggestion_title")
        if title:
            return str(title)
    return None
