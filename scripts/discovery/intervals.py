from __future__ import annotations

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


def select_rows(
    rows: list[dict[str, Any]],
    interval_indexes: str | None,
    start: int,
    limit: int | None,
) -> list[dict[str, Any]]:
    selected_indexes = parse_interval_indexes(interval_indexes)
    if selected_indexes is not None:
        rows = [row for row in rows if int(row["interval_index"]) in selected_indexes]

    rows = rows[start:]
    if limit is not None:
        rows = rows[:limit]
    return rows

