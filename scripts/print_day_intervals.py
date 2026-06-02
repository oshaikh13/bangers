#!/usr/bin/env python3
"""Print discovery interval counts for each zero-based day selector."""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from discovery.intervals import interval_day_key
from discovery.paths import DEFAULT_INTERVAL_MINUTES, default_intervals_path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid JSON in {path}:{line_num}: {exc}") from exc
            if not isinstance(row, dict):
                raise SystemExit(f"expected JSON object in {path}:{line_num}")
            rows.append(row)
    return rows


def interval_index_range(first: int, last: int) -> str:
    return str(first) if first == last else f"{first}-{last}"


def print_day_intervals(rows: list[dict[str, Any]]) -> None:
    counts: OrderedDict[str, int] = OrderedDict()
    index_ranges: OrderedDict[str, list[int]] = OrderedDict()

    for row in rows:
        day = interval_day_key(row)
        try:
            interval_index = int(row["interval_index"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SystemExit(f"row is missing integer interval_index: {row}") from exc

        counts[day] = counts.get(day, 0) + 1
        if day not in index_ranges:
            index_ranges[day] = [interval_index, interval_index]
        else:
            index_ranges[day][1] = interval_index

    print(f"{'day':>3}  {'date':<10}  {'intervals':>9}  interval_indexes")
    print(f"{'---':>3}  {'----------':<10}  {'---------':>9}  ----------------")
    for day_index, (day, count) in enumerate(counts.items()):
        first, last = index_ranges[day]
        index_label = interval_index_range(first, last)
        print(f"{day_index:>3}  {day:<10}  {count:>9}  {index_label}")

    print()
    print(f"total_days: {len(counts)}")
    print(f"total_intervals: {sum(counts.values())}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "minutes",
        type=int,
        nargs="?",
        default=DEFAULT_INTERVAL_MINUTES,
        help="Interval size in minutes. Defaults to 15.",
    )
    parser.add_argument(
        "--intervals",
        type=Path,
        help=(
            "Input interval JSONL. Defaults to "
            "data/log_intervals_<minutes>m.jsonl."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.minutes <= 0:
        raise SystemExit("minutes must be greater than 0")

    intervals = args.intervals or default_intervals_path(args.minutes)
    if not intervals.exists():
        raise SystemExit(f"interval JSONL not found: {intervals}")

    rows = read_jsonl(intervals)
    if not rows:
        raise SystemExit(f"interval JSONL is empty: {intervals}")
    print_day_intervals(rows)


if __name__ == "__main__":
    main()
