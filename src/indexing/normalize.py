"""Normalize 5 non-audio connector logs to canonical UTC envelope.

Reads powernap/logs/<connector>/filtered.jsonl, normalizes inner timestamps,
writes ama/staging/<connector>.jsonl. Drops rows with ts < 2026-04-06T00:00Z.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

CUTOVER_TS = 1775433600.0  # 2026-04-06T00:00:00Z
COCOA_OFFSET = 978307200   # seconds between 2001-01-01 UTC and unix epoch

CONNECTORS = ["screen", "calendar", "email", "notifications", "filesys"]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOGS = REPO_ROOT.parent / "powernap" / "logs"
DEFAULT_STAGING = REPO_ROOT / "staging"


def ts_to_iso(ts: float) -> str:
    return (
        datetime.fromtimestamp(ts, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def normalize_screen(source: dict) -> dict:
    if "start_time" in source:
        source["start_time_local"] = source.pop("start_time")
    # Heavy fields kept in powernap/logs/screen/labels.jsonl; trim from index.
    source.pop("raw_events", None)
    source.pop("screenshot_path", None)
    return source


def normalize_calendar(source: dict) -> dict:
    return source


def normalize_email(source: dict) -> dict:
    raw_date = source.get("date")
    if raw_date:
        dt = parsedate_to_datetime(raw_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        source["date_utc_iso"] = (
            dt.astimezone(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )
    return source


def normalize_notifications(source: dict) -> dict:
    if "timestamp" in source and isinstance(source["timestamp"], (int, float)):
        source["timestamp"] = source["timestamp"] + COCOA_OFFSET
    return source


def normalize_filesys(source: dict) -> dict:
    return source


NORMALIZERS = {
    "screen": normalize_screen,
    "calendar": normalize_calendar,
    "email": normalize_email,
    "notifications": normalize_notifications,
    "filesys": normalize_filesys,
}


def normalize_connector(name: str, logs_dir: Path, staging_dir: Path) -> int:
    src = logs_dir / name / "filtered.jsonl"
    dst = staging_dir / f"{name}.jsonl"
    normalizer = NORMALIZERS[name]

    rows = []
    with src.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            ts = obj.get("timestamp")
            if ts is None or ts < CUTOVER_TS:
                continue
            source = obj.get("source", {})
            source = normalizer(source)
            rows.append({
                "ts": ts,
                "ts_iso": ts_to_iso(ts),
                "connector": name,
                "text": obj.get("text", ""),
                "source": source,
            })

    rows.sort(key=lambda r: r["ts"])
    with dst.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--connector",
        choices=CONNECTORS + ["all"],
        default="all",
    )
    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=Path(os.environ.get("POWERNAP_LOGS_DIR", str(DEFAULT_LOGS))),
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=Path(os.environ.get("STAGING_DIR", str(DEFAULT_STAGING))),
    )
    args = parser.parse_args()

    args.staging_dir.mkdir(parents=True, exist_ok=True)
    targets = CONNECTORS if args.connector == "all" else [args.connector]
    for name in targets:
        n = normalize_connector(name, args.logs_dir, args.staging_dir)
        print(f"{name}: {n} rows → {args.staging_dir / f'{name}.jsonl'}")


if __name__ == "__main__":
    main()
