from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


QUESTION_CONTEXT_EVENT_COUNT = 100
THREAD_COUNT = 3
MIN_QAS_PER_THREAD = 3
MAX_QAS_PER_THREAD = 10


def parse_timestamp(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value:
        return None

    timestamp = value
    if timestamp.endswith("Z"):
        timestamp = f"{timestamp[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def format_ts_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace(
        "+00:00",
        "Z",
    )


def load_indexed_events(logs_dir: Path) -> list[dict[str, Any]]:
    if not logs_dir.exists():
        raise SystemExit(f"logs-indexed directory not found: {logs_dir}")

    sortable_events: list[tuple[tuple[float, str, int], dict[str, Any]]] = []
    for path in sorted(logs_dir.glob("*/*.jsonl")):
        if any(part.startswith(".") for part in path.relative_to(logs_dir).parts):
            continue
        connector_from_path = path.parent.name
        with path.open(encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue

                ts = parse_timestamp(record.get("ts"))
                if ts is None:
                    continue

                source = record.get("source")
                text = record.get("text")
                if not isinstance(text, str) or not text:
                    text = _source_fallback_text(source)

                connector = record.get("connector")
                if not isinstance(connector, str) or not connector:
                    connector = connector_from_path

                ts_iso = record.get("ts_iso")
                if not isinstance(ts_iso, str) or not ts_iso:
                    ts_iso = format_ts_iso(ts)

                event = {
                    "ts": ts,
                    "ts_iso": ts_iso,
                    "connector": connector,
                    "text": text,
                }
                sortable_events.append(((ts, str(path), line_number), event))

    sortable_events.sort(key=lambda item: item[0])
    return [event for _, event in sortable_events]


def _source_fallback_text(source: Any) -> str:
    if not isinstance(source, dict):
        return ""
    for key in ("summary", "dense_caption", "title", "subject"):
        value = source.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def context_events_for_timestamp(
    events: Iterable[dict[str, Any]],
    timestamp: Any,
    limit: int = QUESTION_CONTEXT_EVENT_COUNT,
) -> list[dict[str, Any]]:
    cutoff_ts = parse_timestamp(timestamp)
    if cutoff_ts is None:
        raise RuntimeError(f"could not parse banger timestamp: {timestamp!r}")
    if limit <= 0:
        raise RuntimeError(f"context event limit must be positive: {limit}")

    selected = [
        event
        for event in events
        if isinstance(event.get("ts"), (int, float))
        and float(event["ts"]) <= cutoff_ts
    ][-limit:]

    return [
        {
            "index": index,
            "ts": float(event["ts"]),
            "ts_iso": str(event.get("ts_iso", format_ts_iso(float(event["ts"])))),
            "connector": str(event.get("connector", "")),
            "text": str(event.get("text", "")),
        }
        for index, event in enumerate(selected)
    ]


def training_context_projection(
    context_events: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "index": event.get("index"),
            "ts": event.get("ts"),
            "ts_iso": event.get("ts_iso"),
            "connector": event.get("connector"),
            "text": event.get("text"),
        }
        for event in context_events
        if isinstance(event, dict)
    ]


def training_rows_from_final_questions(items: Iterable[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        questions = item.get("questions")
        if not isinstance(questions, dict):
            questions = item.get("qa")
        if not isinstance(questions, dict):
            questions = item

        qa_type = questions.get("qa_type")
        if not isinstance(qa_type, str):
            qa_type = item.get("qa_type")
        if not isinstance(qa_type, str):
            qa_type = None

        context_events = questions.get("context_events")
        if not isinstance(context_events, list):
            context_events = item.get("context_events")
        if not isinstance(context_events, list):
            continue

        projected_context = training_context_projection(context_events)

        thread_batches: list[tuple[Any, list[Any]]] = []
        threads = questions.get("threads")
        if isinstance(threads, list):
            for thread in threads:
                if not isinstance(thread, dict):
                    continue
                pairs = thread.get("qa_pairs")
                if isinstance(pairs, list):
                    thread_batches.append((thread.get("thread_id"), pairs))
        else:
            flat_pairs = questions.get("qa_pairs")
            if isinstance(flat_pairs, list):
                thread_batches.append((0, flat_pairs))

        for thread_id, qa_pairs in thread_batches:
            for pair in qa_pairs:
                if not isinstance(pair, dict):
                    continue
                question = pair.get("question")
                answer = pair.get("answer")
                if not isinstance(question, str) or not isinstance(answer, str):
                    continue
                row = {
                    "context_events": projected_context,
                    "thread_id": thread_id,
                    "q_id": pair.get("q_id"),
                    "question": question,
                    "answer": answer,
                }
                category = pair.get("category")
                if isinstance(category, str) and category:
                    row["category"] = category
                if qa_type is not None:
                    row["qa_type"] = qa_type
                rows.append(row)
    return rows
