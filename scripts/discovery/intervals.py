from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_interval_indexes(raw: str | None) -> set[int] | None:
    if not raw:
        return None

    indexes: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_raw, end_raw = part.split("-", 1)
            start = int(start_raw)
            end = int(end_raw)
            if end < start:
                raise SystemExit(f"invalid interval range: {part}")
            indexes.update(range(start, end + 1))
        else:
            indexes.add(int(part))
    return indexes


def parse_day_indexes(raw: str | None) -> set[int] | None:
    if not raw:
        return None
    indexes = parse_interval_indexes(raw)
    if indexes is None:
        return None
    if any(index < 0 for index in indexes):
        raise SystemExit("--days uses zero-based day numbers")
    return indexes


def interval_day_key(row: dict[str, Any]) -> str:
    for key in ("start_local", "start_utc"):
        value = row.get(key)
        if isinstance(value, str) and len(value) >= 10:
            return value[:10]

    ts = row.get("start_ts")
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).date().isoformat()

    raise RuntimeError(f"could not derive interval day: {row}")


def day_index_by_key(rows: list[dict[str, Any]]) -> dict[str, int]:
    day_by_key: dict[str, int] = {}
    for row in rows:
        day = interval_day_key(row)
        if day not in day_by_key:
            day_by_key[day] = len(day_by_key)
    return day_by_key


def interval_indexes_for_days(
    rows: list[dict[str, Any]],
    raw_days: str | None,
) -> set[int] | None:
    selected_days = parse_day_indexes(raw_days)
    if selected_days is None:
        return None

    day_by_key = day_index_by_key(rows)
    selected = {
        int(row["interval_index"])
        for row in rows
        if day_by_key[interval_day_key(row)] in selected_days
    }
    if not selected:
        print("no interval rows selected by --days")
    return selected


def select_rows(
    rows: list[dict[str, Any]],
    interval_indexes: str | None,
    days: str | None,
    start: int,
    limit: int | None,
) -> list[dict[str, Any]]:
    selected_indexes = parse_interval_indexes(interval_indexes)
    day_indexes = interval_indexes_for_days(rows, days)
    if selected_indexes is not None and day_indexes is not None:
        selected_indexes &= day_indexes
    elif day_indexes is not None:
        selected_indexes = day_indexes

    if selected_indexes is not None:
        rows = [row for row in rows if int(row["interval_index"]) in selected_indexes]

    rows = rows[start:]
    if limit is not None:
        rows = rows[:limit]
    return rows
