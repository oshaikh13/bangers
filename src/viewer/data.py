from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

GOAL_PATTERN = re.compile(r"^goal_(\d+)\.json$")
BANGER_PATTERN = re.compile(r"^banger_(\d+)\.json$")
BANGERS_PATTERN = re.compile(r"^bangers_(\d+)_(\d+)\.json$")
QUESTION_PATTERN = re.compile(r"^question_(.+)\.json$")
GENERIC_QA_DIR = "10_generic_qa"
GENERIC_QA_FILE_PATTERN = re.compile(r"^qa_(\d+)\.json$")
GENERIC_QA_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
PRE_BANGER_QA_DIR = "20_pre_banger_qa"
PRE_BANGER_QA_FILE_PATTERN = re.compile(r"^qa_(.+)\.json$")
PRE_BANGER_QA_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
PRE_BANGER_SEED_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")
LOGS_INDEXED_DIR = REPO_ROOT / "logs-indexed"
COMBINED_RELATIVE_PATHS = (
    "02a_combined/combined.json",
    "02_combined/combined.json",
)

_INDEXED_EVENTS_CACHE: list[dict[str, Any]] | None = None


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
    has_generic_qa: bool
    has_pre_banger_qa: bool


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
    generic_qa_dir = path / GENERIC_QA_DIR
    pre_banger_qa_dir = path / PRE_BANGER_QA_DIR
    final_questions = questions_dir / "final_questions.json"
    goal_count = 0
    if goals_dir.is_dir():
        try:
            goal_count = len(load_all_goals(path))
        except (ValueError, OSError):
            goal_count = len(list_goal_intervals(path))
    has_generic_qa = generic_qa_dir.is_dir() and any(
        generic_qa_dir.glob("*/qa_*.json")
    )
    has_pre_banger_qa = pre_banger_qa_dir.is_dir() and any(
        pre_banger_qa_dir.glob("*/qa_*.json")
    )
    return RunInfo(
        name=path.name,
        path=path,
        goal_count=goal_count,
        has_goals=goal_count > 0,
        has_combined=resolve_combined_path(path) is not None,
        has_bangers=any(bangers_dir.glob("bangers_*.json"))
        or any(bangers_dir.glob("banger_*.json")),
        has_questions=final_questions.is_file() or any(
            questions_dir.glob("question_*.json")
        ),
        has_generic_qa=has_generic_qa,
        has_pre_banger_qa=has_pre_banger_qa,
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
    paths = sorted(
        [*bangers_dir.glob("bangers_*.json"), *bangers_dir.glob("banger_*.json")]
    )
    for path in paths:
        batch_match = BANGERS_PATTERN.match(path.name)
        if batch_match:
            data = load_json(path)
            bangers = data.get("bangers") if isinstance(data, dict) else None
            if not isinstance(bangers, list):
                continue
            for item in bangers:
                if not isinstance(item, dict):
                    continue
                combined_index = item.get("input_index")
                if isinstance(combined_index, int):
                    indexes.append(
                        {"combined_index": combined_index, "path": path.name}
                    )
            continue
        match = BANGER_PATTERN.match(path.name)
        if not match:
            continue
        combined_index = int(match.group(1))
        indexes.append({"combined_index": combined_index, "path": path.name})
    indexes.sort(key=lambda item: item["combined_index"])
    return indexes


def load_banger(run_path: Path, combined_index: int) -> dict[str, Any]:
    bangers_dir = run_path / "03_bangers"
    legacy_path = bangers_dir / f"banger_{combined_index}.json"
    if legacy_path.is_file():
        data = load_json(legacy_path)
        if not isinstance(data, dict):
            raise ValueError(f"expected banger object in {legacy_path.name}")
        return data

    for path in sorted(bangers_dir.glob("bangers_*.json")):
        match = BANGERS_PATTERN.match(path.name)
        if not match:
            continue
        start_index, end_index = int(match.group(1)), int(match.group(2))
        if not start_index <= combined_index <= end_index:
            continue
        data = load_json(path)
        bangers = data.get("bangers") if isinstance(data, dict) else None
        if not isinstance(bangers, list):
            raise ValueError(f"expected bangers array in {path.name}")
        for item in bangers:
            if isinstance(item, dict) and item.get("input_index") == combined_index:
                return {"goals": item.get("goals", [])}
    raise FileNotFoundError(f"banger file not found for input {combined_index}")


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
    generic_qa = list_generic_qa_items(run_path) if run.has_generic_qa else []
    pre_banger_qa = (
        list_pre_banger_qa_items(run_path) if run.has_pre_banger_qa else []
    )

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
            "generic_qa": run.has_generic_qa,
            "pre_banger_qa": run.has_pre_banger_qa,
        },
        "counts": {
            "goals": len(goals),
            "combined": len(combined_items),
            "bangers": len(bangers),
            "questions": len(questions),
            "generic_qa": len(generic_qa),
            "pre_banger_qa": len(pre_banger_qa),
        },
        "goals": goals,
        "combined": combined_items,
        "bangers": bangers,
        "questions": questions,
        "generic_qa": generic_qa,
        "pre_banger_qa": pre_banger_qa,
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


def _generic_qa_pairs(data: Any) -> list[Any]:
    """Return qa_pairs from either the flat or legacy threaded shape."""
    if not isinstance(data, dict):
        return []
    flat = data.get("qa_pairs")
    if isinstance(flat, list):
        return flat
    collected: list[Any] = []
    threads = data.get("threads")
    if isinstance(threads, list):
        for thread in threads:
            if isinstance(thread, dict):
                pairs = thread.get("qa_pairs")
                if isinstance(pairs, list):
                    collected.extend(pairs)
    return collected


def list_generic_qa_items(run_path: Path) -> list[dict[str, Any]]:
    base = run_path / GENERIC_QA_DIR
    if not base.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for qa_type_dir in sorted(base.iterdir()):
        if not qa_type_dir.is_dir() or not GENERIC_QA_TYPE_PATTERN.match(qa_type_dir.name):
            continue
        qa_type = qa_type_dir.name
        for path in sorted(qa_type_dir.glob("qa_*.json")):
            match = GENERIC_QA_FILE_PATTERN.match(path.name)
            if not match:
                continue
            interval = int(match.group(1))
            try:
                data = load_json(path)
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            qa_timestamp = data.get("qa_timestamp")
            qa_timestamp_ts = data.get("qa_timestamp_ts")
            if not isinstance(qa_timestamp_ts, (int, float)):
                qa_timestamp_ts = None
            pair_count = 0
            sample_question: str | None = None
            pairs = _generic_qa_pairs(data)
            pair_count = len(pairs)
            for pair in pairs:
                if isinstance(pair, dict):
                    text = pair.get("question")
                    if isinstance(text, str) and text:
                        sample_question = text
                        break
            items.append(
                {
                    "qa_type": qa_type,
                    "interval_index": interval,
                    "qa_timestamp": qa_timestamp,
                    "qa_timestamp_ts": qa_timestamp_ts,
                    "pair_count": pair_count,
                    "sample_question": sample_question,
                }
            )
    items.sort(
        key=lambda item: (
            item["qa_timestamp_ts"] if item["qa_timestamp_ts"] is not None else float("inf"),
            item["qa_type"],
            item["interval_index"],
        )
    )
    return items


def load_generic_qa(run_path: Path, qa_type: str, interval: int) -> dict[str, Any]:
    if not GENERIC_QA_TYPE_PATTERN.match(qa_type or ""):
        raise FileNotFoundError(f"invalid qa_type: {qa_type!r}")
    path = run_path / GENERIC_QA_DIR / qa_type / f"qa_{interval}.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"generic qa file not found: {qa_type}/qa_{interval}.json"
        )
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"expected object in {path.name}")
    return data


def _parse_timestamp(value: Any) -> float | None:
    from discovery.question_context import parse_timestamp

    return parse_timestamp(value)


def list_pre_banger_qa_items(run_path: Path) -> list[dict[str, Any]]:
    base = run_path / PRE_BANGER_QA_DIR
    if not base.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for qa_type_dir in sorted(base.iterdir()):
        if not qa_type_dir.is_dir() or not PRE_BANGER_QA_TYPE_PATTERN.match(
            qa_type_dir.name
        ):
            continue
        qa_type = qa_type_dir.name
        for path in sorted(qa_type_dir.glob("qa_*.json")):
            match = PRE_BANGER_QA_FILE_PATTERN.match(path.name)
            if not match:
                continue
            seed_id = match.group(1)
            try:
                data = load_json(path)
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict):
                continue
            banger_timestamp = data.get("banger_timestamp")
            banger_timestamp_ts = _parse_timestamp(banger_timestamp)
            pairs = _generic_qa_pairs(data)
            pair_count = len(pairs)
            sample_question: str | None = None
            for pair in pairs:
                if isinstance(pair, dict):
                    text = pair.get("question")
                    if isinstance(text, str) and text:
                        sample_question = text
                        break
            items.append(
                {
                    "qa_type": qa_type,
                    "seed_id": seed_id,
                    "banger_timestamp": banger_timestamp,
                    "banger_timestamp_ts": banger_timestamp_ts,
                    "pair_count": pair_count,
                    "sample_question": sample_question,
                }
            )
    items.sort(
        key=lambda item: (
            item["banger_timestamp_ts"]
            if item["banger_timestamp_ts"] is not None
            else float("inf"),
            item["qa_type"],
            item["seed_id"],
        )
    )
    return items


def load_pre_banger_qa(run_path: Path, qa_type: str, seed_id: str) -> dict[str, Any]:
    if not PRE_BANGER_QA_TYPE_PATTERN.match(qa_type or ""):
        raise FileNotFoundError(f"invalid qa_type: {qa_type!r}")
    if not PRE_BANGER_SEED_ID_PATTERN.match(seed_id or ""):
        raise FileNotFoundError(f"invalid seed_id: {seed_id!r}")
    path = run_path / PRE_BANGER_QA_DIR / qa_type / f"qa_{seed_id}.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"pre-banger qa file not found: {qa_type}/qa_{seed_id}.json"
        )
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"expected object in {path.name}")
    if data.get("banger_timestamp_ts") is None:
        ts = _parse_timestamp(data.get("banger_timestamp"))
        if ts is not None:
            data = {**data, "banger_timestamp_ts": ts}
    return data


def _indexed_events() -> list[dict[str, Any]]:
    global _INDEXED_EVENTS_CACHE
    if _INDEXED_EVENTS_CACHE is None:
        from discovery.question_context import load_indexed_events

        _INDEXED_EVENTS_CACHE = load_indexed_events(LOGS_INDEXED_DIR)
    return _INDEXED_EVENTS_CACHE


def load_logs_window(
    center_ts: float,
    before: int = 200,
    after: int = 200,
) -> dict[str, Any]:
    events = _indexed_events()
    past = [event for event in events if float(event["ts"]) <= center_ts]
    future = [event for event in events if float(event["ts"]) > center_ts]
    past_window = past[-before:] if before > 0 else []
    future_window = future[:after] if after > 0 else []
    return {
        "center_ts": center_ts,
        "before_count": len(past_window),
        "after_count": len(future_window),
        "before_available": len(past),
        "after_available": len(future),
        "past": past_window,
        "future": future_window,
    }
