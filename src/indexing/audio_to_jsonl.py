"""Parse powernap/logs/audio/*.md into 2-minute chunk records.

Each chunk header `## HH:MM:SS – HH:MM:SS` (LOCAL time, America/Los_Angeles)
becomes one canonical envelope row in ama/staging/audio.jsonl. Drops chunks
with ts < 2026-04-06T00:00Z. Handles midnight-crossing within a session file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CUTOVER_TS = 1775433600.0  # 2026-04-06T00:00:00Z
LOCAL_TZ = ZoneInfo("America/Los_Angeles")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOGS = REPO_ROOT.parent / "powernap" / "logs"
DEFAULT_STAGING = REPO_ROOT / "staging"

FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_\d{2}-\d{2}-\d{2}\.md$")
CHUNK_HEADER_RE = re.compile(
    r"^##\s+(\d{2}):(\d{2}):(\d{2})\s*[–—\-]\s*(\d{2}):(\d{2}):(\d{2})\s*$"
)
LINE_OFFSET_RE = re.compile(r"^\[(\d{2}):(\d{2})(?::(\d{3}))?\]\s*(.*)$")


def ts_to_iso(ts: float) -> str:
    return (
        datetime.fromtimestamp(ts, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def parse_lines_block(body_lines: list[str]) -> tuple[list[dict], str]:
    """Strip per-line `[MM:SS]` / `[MM:SS:mmm]` offsets into a parallel array.
    Returns (lines_with_offsets, full_transcript_text).
    """
    lines: list[dict] = []
    transcript_parts: list[str] = []
    for raw in body_lines:
        s = raw.rstrip("\n")
        if not s.strip():
            continue
        m = LINE_OFFSET_RE.match(s)
        if m:
            mm, ss, mmm, text = m.groups()
            offset = int(mm) * 60 + int(ss) + (int(mmm) / 1000.0 if mmm else 0.0)
            lines.append({"offset_s": offset, "text": text})
            transcript_parts.append(text)
        else:
            transcript_parts.append(s)
    return lines, " ".join(transcript_parts)


def parse_audio_file(path: Path) -> list[dict]:
    """Return canonical envelope rows for every chunk in one .md file."""
    m = FILENAME_RE.match(path.name)
    if not m:
        return []
    base_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find chunk header positions
    headers: list[tuple[int, time, time]] = []
    for i, line in enumerate(lines):
        hm = CHUNK_HEADER_RE.match(line)
        if not hm:
            continue
        sh, sm, ss, eh, em, es = (int(x) for x in hm.groups())
        headers.append(
            (i, time(sh, sm, ss), time(eh, em, es))
        )

    if not headers:
        return []

    rows: list[dict] = []
    day_offset = 0
    prev_local = None

    for idx, (line_i, start_t, end_t) in enumerate(headers):
        # Chunk body = lines until next chunk header or EOF
        end_i = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        body = lines[line_i + 1:end_i]
        line_records, transcript = parse_lines_block(body)

        # Build local datetime; bump day if start time wraps backwards
        candidate = datetime.combine(
            base_date + timedelta(days=day_offset), start_t, tzinfo=LOCAL_TZ
        )
        if prev_local is not None and candidate < prev_local:
            day_offset += 1
            candidate = datetime.combine(
                base_date + timedelta(days=day_offset), start_t, tzinfo=LOCAL_TZ
            )
        prev_local = candidate

        utc_dt = candidate.astimezone(timezone.utc)
        ts = utc_dt.timestamp()

        # Duration: end_t may also wrap past midnight relative to start_t
        end_candidate = datetime.combine(
            base_date + timedelta(days=day_offset), end_t, tzinfo=LOCAL_TZ
        )
        if end_candidate < candidate:
            end_candidate = datetime.combine(
                base_date + timedelta(days=day_offset + 1), end_t, tzinfo=LOCAL_TZ
            )
        duration_s = (end_candidate - candidate).total_seconds()

        rows.append({
            "ts": ts,
            "ts_iso": ts_to_iso(ts),
            "connector": "audio",
            "text": transcript[:200],
            "source": {
                "file": path.name,
                "chunk_start_local": start_t.strftime("%H:%M:%S"),
                "chunk_end_local": end_t.strftime("%H:%M:%S"),
                "duration_s": duration_s,
                "transcript": transcript,
                "lines": line_records,
            },
        })

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
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

    audio_dir = args.logs_dir / "audio"
    out_path = args.staging_dir / "audio.jsonl"
    args.staging_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in audio_dir.glob("*.md") if FILENAME_RE.match(p.name))
    all_rows: list[dict] = []
    for f in files:
        all_rows.extend(parse_audio_file(f))

    kept = [r for r in all_rows if r["ts"] >= CUTOVER_TS]
    kept.sort(key=lambda r: r["ts"])

    with out_path.open("w") as f:
        for row in kept:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")
    print(f"audio: {len(kept)} chunks (of {len(all_rows)} parsed) → {out_path}")


if __name__ == "__main__":
    main()
