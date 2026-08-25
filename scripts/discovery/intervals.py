from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def interval_day_key(row: dict[str, Any]) -> str:
    for key in ("start_local", "start_utc"):
        value = row.get(key)
        if isinstance(value, str) and len(value) >= 10:
            return value[:10]

    ts = row.get("start_ts")
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).date().isoformat()

    raise RuntimeError(f"could not derive interval day: {row}")


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


def parse_interval_range(raw: str | None) -> tuple[int, int] | None:
    if not raw:
        return None
    if "," in raw:
        raise SystemExit("--interval-range accepts one inclusive START-END range")
    if "-" not in raw:
        raise SystemExit("--interval-range must use START-END")
    start_raw, end_raw = raw.split("-", 1)
    start = int(start_raw)
    end = int(end_raw)
    if start < 0 or end < 0:
        raise SystemExit("--interval-range indexes must be non-negative")
    if end < start:
        raise SystemExit(f"invalid interval range: {raw}")
    return start, end


def interval_range_indexes(raw: str | None) -> set[int] | None:
    parsed = parse_interval_range(raw)
    if parsed is None:
        return None
    start, end = parsed
    return set(range(start, end + 1))


def select_rows(
    rows: list[dict[str, Any]],
    interval_range: str | None,
    start: int,
    limit: int | None,
) -> list[dict[str, Any]]:
    selected_indexes = interval_range_indexes(interval_range)

    if selected_indexes is not None:
        rows = [row for row in rows if int(row["interval_index"]) in selected_indexes]

    rows = rows[start:]
    if limit is not None:
        rows = rows[:limit]
    return rows
