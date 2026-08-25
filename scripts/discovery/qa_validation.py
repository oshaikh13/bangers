from __future__ import annotations

from pathlib import Path
from typing import Any

from .question_context import QUESTION_CONTEXT_EVENT_COUNT, parse_timestamp


ANSWER_BASES = {"H", "F", "H+F"}
TIMESCALES = {"micro", "short", "medium", "long"}

# verify_at_ts arrives as an epoch float that can carry sub-millisecond precision,
# while the cutoff (qa/banger timestamp) comes from a millisecond-precision ISO
# string. Compare with a 1ms tolerance so a verify time sitting on the cutoff
# instant is not spuriously read as "after" it. The cutoff instant counts as
# observable hindsight, so it is valid for H as well as F/H+F.
VERIFY_TS_TOLERANCE_SECONDS = 1e-3


def valid_context_indexes(data: dict[str, Any], path: Path | str, label: str) -> set[int]:
    context_events = data.get("context_events")
    if not isinstance(context_events, list):
        raise RuntimeError(f"{label} output must include context_events: {path}")
    if len(context_events) > QUESTION_CONTEXT_EVENT_COUNT:
        raise RuntimeError(
            f"{label} context_events must have at most "
            f"{QUESTION_CONTEXT_EVENT_COUNT} events: {path}"
        )

    indexes: set[int] = set()
    for index, event in enumerate(context_events):
        if not isinstance(event, dict):
            raise RuntimeError(f"{label} context_events[{index}] must be an object: {path}")
        if event.get("index") != index:
            raise RuntimeError(f"{label} context_events indexes must be contiguous from 0: {path}")
        indexes.add(index)
    return indexes


def require_text_fields(
    pair: dict[str, Any],
    keys: tuple[str, ...],
    location: str,
    path: Path | str,
    label: str,
) -> None:
    for key in keys:
        if not isinstance(pair.get(key), str) or not pair.get(key):
            raise RuntimeError(f"{label} output {location}.{key} must be a non-empty string: {path}")


def validate_question_basis(
    pair: dict[str, Any],
    location: str,
    valid_indexes: set[int],
    path: Path | str,
    label: str,
) -> None:
    question_basis = pair.get("question_basis")
    if not isinstance(question_basis, dict):
        raise RuntimeError(f"{label} output {location}.question_basis must be an object: {path}")
    reason = question_basis.get("reason")
    if not isinstance(reason, str) or not reason:
        raise RuntimeError(
            f"{label} output {location}.question_basis.reason must be a non-empty string: {path}"
        )
    basis_indexes = question_basis.get("context_event_indexes")
    if not isinstance(basis_indexes, list) or not basis_indexes:
        raise RuntimeError(
            f"{label} output {location}.question_basis.context_event_indexes "
            f"must be a non-empty array: {path}"
        )
    for basis_index in basis_indexes:
        if not isinstance(basis_index, int):
            raise RuntimeError(
                f"{label} output {location}.question_basis.context_event_indexes "
                f"must contain integers: {path}"
            )
        if basis_index not in valid_indexes:
            raise RuntimeError(
                f"{label} output {location} references missing context event index "
                f"{basis_index}: {path}"
            )


def validate_grounded_pair(
    pair: Any,
    pair_index: int,
    location: str,
    cutoff_ts: float,
    valid_indexes: set[int],
    path: Path | str,
    label: str,
    cutoff_name: str,
) -> None:
    if not isinstance(pair, dict):
        raise RuntimeError(f"{label} output {location} must be an object: {path}")
    if not isinstance(pair.get("q_id"), int):
        raise RuntimeError(f"{label} output {location}.q_id must be an integer: {path}")

    for key in (
        "question",
        "answer",
        "category",
        "timescale",
        "answer_basis",
        "verify_at_ts",
        "verify_at_iso",
        "question_basis",
        "why_it_matters",
        "evidence_grounding",
        "question_difficulty",
    ):
        if key not in pair:
            raise RuntimeError(f"{label} output {location} must include {key}: {path}")

    require_text_fields(
        pair,
        ("question", "answer", "category", "why_it_matters", "evidence_grounding"),
        location,
        path,
        label,
    )

    if pair.get("timescale") not in TIMESCALES:
        raise RuntimeError(
            f"{label} output {location}.timescale must be one of {sorted(TIMESCALES)}: {path}"
        )

    answer_basis = pair.get("answer_basis")
    if answer_basis not in ANSWER_BASES:
        raise RuntimeError(f"{label} output {location}.answer_basis must be H, F, or H+F: {path}")

    verify_at_ts = parse_timestamp(pair.get("verify_at_ts"))
    if verify_at_ts is None:
        raise RuntimeError(f"{label} output {location}.verify_at_ts must be parseable: {path}")
    if answer_basis == "H" and verify_at_ts > cutoff_ts + VERIFY_TS_TOLERANCE_SECONDS:
        raise RuntimeError(
            f"{label} output {location}.verify_at_ts must be at or before "
            f"{cutoff_name} for H answers: {path}"
        )
    if (
        answer_basis in {"F", "H+F"}
        and verify_at_ts < cutoff_ts - VERIFY_TS_TOLERANCE_SECONDS
    ):
        raise RuntimeError(
            f"{label} output {location}.verify_at_ts must be at or after "
            f"{cutoff_name} for {answer_basis} answers: {path}"
        )

    if not isinstance(pair.get("question_difficulty"), (int, float)):
        raise RuntimeError(f"{label} output {location}.question_difficulty must be a number: {path}")

    validate_question_basis(pair, location, valid_indexes, path, label)
