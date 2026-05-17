#!/usr/bin/env python3
"""Record active 15-minute intervals across the indexed log timespan.

Scans logs-indexed/**/*.jsonl for canonical rows with `ts` or `ts_iso`, finds
the earliest and latest event timestamps, and writes one JSONL row per interval
that contains activity. Each row includes UTC/local boundaries and event counts
by connector.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:
    ZoneInfo = None

LOCAL_TZ_NAME = "America/Los_Angeles"
LOCAL_TZ = ZoneInfo(LOCAL_TZ_NAME) if ZoneInfo else None
INTERVAL_SECONDS = 15 * 60

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOGS_INDEXED = REPO_ROOT / "logs-indexed"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "log_intervals_15m.jsonl"


def iso_utc(ts: float) -> str:
    return (
        datetime.fromtimestamp(ts, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def iso_local(ts: float) -> str:
    if LOCAL_TZ:
        return datetime.fromtimestamp(ts, tz=LOCAL_TZ).isoformat(timespec="milliseconds")

    previous_tz = os.environ.get("TZ")
    os.environ["TZ"] = LOCAL_TZ_NAME
    time.tzset()
    try:
        return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="milliseconds")
    finally:
        if previous_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous_tz
        time.tzset()


def parse_ts(row: dict) -> float | None:
    ts = row.get("ts")
    if isinstance(ts, (int, float)):
        return float(ts)

    ts_iso = row.get("ts_iso")
    if isinstance(ts_iso, str):
        try:
            return datetime.fromisoformat(ts_iso.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None

    return None


def iter_jsonl_files(logs_indexed_dir: Path):
    for path in sorted(logs_indexed_dir.rglob("*.jsonl")):
        if ".git" in path.parts:
            continue
        yield path


def iter_events(logs_indexed_dir: Path):
    for path in iter_jsonl_files(logs_indexed_dir):
        connector = path.parent.name
        with path.open(encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(
                        f"warning: skipping invalid JSON in {path}:{line_num}: {exc}",
                        file=sys.stderr,
                    )
                    continue

                ts = parse_ts(row)
                if ts is None:
                    print(
                        f"warning: skipping row without timestamp in {path}:{line_num}",
                        file=sys.stderr,
                    )
                    continue

                yield {
                    "ts": ts,
                    "connector": row.get("connector") or connector,
                    "path": path,
                    "line": line_num,
                }


def load_events(logs_indexed_dir: Path) -> list[dict]:
    return sorted(iter_events(logs_indexed_dir), key=lambda event: event["ts"])


def build_interval_records(
    events: list[dict],
    interval_seconds: int,
    include_empty: bool,
) -> list[dict]:
    if not events:
        return []

    start_ts = events[0]["ts"]
    end_ts = events[-1]["ts"]
    interval_count = max(1, math.ceil((end_ts - start_ts) / interval_seconds))
    records = []

    event_i = 0
    total_events = len(events)
    for interval_i in range(interval_count):
        interval_start = start_ts + interval_i * interval_seconds
        interval_end = min(start_ts + (interval_i + 1) * interval_seconds, end_ts)
        is_last = interval_i == interval_count - 1

        connector_counts: Counter[str] = Counter()
        interval_events = 0
        while event_i < total_events:
            event = events[event_i]
            in_interval = (
                interval_start <= event["ts"] <= interval_end
                if is_last
                else interval_start <= event["ts"] < interval_end
            )
            if not in_interval:
                break

            connector_counts[str(event["connector"])] += 1
            interval_events += 1
            event_i += 1

        if include_empty or interval_events > 0:
            records.append(
                {
                    "interval_index": interval_i,
                    "start_ts": interval_start,
                    "end_ts": interval_end,
                    "start_utc": iso_utc(interval_start),
                    "end_utc": iso_utc(interval_end),
                    "start_local": iso_local(interval_start),
                    "end_local": iso_local(interval_end),
                    "duration_seconds": round(interval_end - interval_start, 6),
                    "event_count": interval_events,
                    "connector_counts": dict(sorted(connector_counts.items())),
                }
            )

    return records


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--logs-indexed-dir",
        type=Path,
        default=Path(os.environ.get("LOGS_INDEXED_DIR", str(DEFAULT_LOGS_INDEXED))),
        help="Directory containing indexed connector JSONL files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(os.environ.get("INTERVALS_OUTPUT", str(DEFAULT_OUTPUT))),
        help="JSONL file to write interval records to.",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=15,
        help="Interval size in minutes.",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        help="Include intervals with no events. By default only active intervals are written.",
    )
    args = parser.parse_args()

    if args.interval_minutes <= 0:
        raise SystemExit("--interval-minutes must be greater than 0")
    if not args.logs_indexed_dir.exists():
        raise SystemExit(f"logs indexed directory not found: {args.logs_indexed_dir}")

    events = load_events(args.logs_indexed_dir)
    if not events:
        raise SystemExit(f"no timestamped events found in {args.logs_indexed_dir}")

    records = build_interval_records(
        events,
        args.interval_minutes * 60,
        include_empty=args.include_empty,
    )
    write_jsonl(args.output, records)

    print(f"events: {len(events)}")
    print(f"active intervals: {len(records)}")
    print(f"start: {records[0]['start_utc']} ({records[0]['start_local']})")
    print(f"end: {records[-1]['end_utc']} ({records[-1]['end_local']})")
    print(f"wrote: {args.output}")


if __name__ == "__main__":
    main()
