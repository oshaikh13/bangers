"""Merge ama/staging/*.jsonl into the logs-indexed/ git repo via fast-import.

Each canonical event becomes one git commit whose author/committer date
equals the event's timestamp, stamped with the local (Pacific) tz offset.
Per-connector files are sharded by *local* day (e.g. screen/2026-04-05.jsonl)
so each commit only rewrites a small file — keeps fast-import work O(N)
instead of O(N²) on the cumulative file size.

Incremental: a per-connector cursor in logs-indexed/.indexer-cursor.json
records the highest-committed ts so re-runs only commit newer rows.
"""

from __future__ import annotations

import argparse
import heapq
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Los_Angeles")

CUTOVER_TS = 1775458800.0  # 2026-04-06T00:00:00-07:00 (= 2026-04-06T07:00:00Z)

CONNECTORS = ["screen", "calendar", "email", "notifications", "filesys", "audio"]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOGS_INDEXED = REPO_ROOT / "logs-indexed"
DEFAULT_STAGING = REPO_ROOT / "staging"
DEFAULT_SCREENSHOTS_DIR = (
    REPO_ROOT.parent / "powernap" / "logs" / "screen" / "labeled_screenshots"
)
SCREENSHOTS_DIR = "screenshots"


def day_key(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=LOCAL_TZ).strftime("%Y-%m-%d")


def local_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=LOCAL_TZ).isoformat(timespec="milliseconds")


def local_tz_offset(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=LOCAL_TZ).strftime("%z")


def out_path(connector: str, ts: float) -> str:
    return f"{connector}/{day_key(ts)}.jsonl"


def run_git(args: list[str], repo: Path, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def init_repo(repo: Path) -> None:
    if (repo / ".git").exists():
        return
    repo.mkdir(parents=True, exist_ok=True)
    run_git(["init", "-b", "main"], repo)
    run_git(["config", "commit.gpgsign", "false"], repo)


def load_cursor(repo: Path) -> dict[str, float]:
    path = repo / ".indexer-cursor.json"
    if not path.exists():
        return {c: CUTOVER_TS for c in CONNECTORS}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c: float(data.get(c, CUTOVER_TS)) for c in CONNECTORS}


def save_cursor(repo: Path, cursor: dict[str, float]) -> None:
    path = repo / ".indexer-cursor.json"
    path.write_text(json.dumps(cursor, indent=2), encoding="utf-8")


def stream_staging(staging: Path, connector: str, after_ts: float):
    src = staging / f"{connector}.jsonl"
    if not src.exists():
        return
    with src.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj["ts"] > after_ts:
                yield obj


def count_pending(staging: Path, cursor: dict[str, float]) -> Counter:
    counts: Counter = Counter()
    for c in CONNECTORS:
        for _ in stream_staging(staging, c, cursor[c]):
            counts[c] += 1
    return counts


def merged_events(staging: Path, cursor: dict[str, float]):
    """Yield all events across connectors in ts-ascending order."""
    iters = [stream_staging(staging, c, cursor[c]) for c in CONNECTORS]
    keyed = (((row["ts"], row) for row in it) for it in iters)
    return (row for _, row in heapq.merge(*keyed, key=lambda kv: kv[0]))


def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def load_existing_buffers(repo: Path) -> dict[str, dict[str, bytearray]]:
    """Read current state of each per-connector per-day file (matches HEAD).

    Returns nested dict: {connector: {day_key: bytearray(...)}}.
    """
    buffers: dict[str, dict[str, bytearray]] = {c: {} for c in CONNECTORS}
    for c in CONNECTORS:
        cdir = repo / c
        if not cdir.is_dir():
            continue
        for f in cdir.glob("*.jsonl"):
            buffers[c][f.stem] = bytearray(f.read_bytes())
    return buffers


def screenshot_source_path(raw_path: str, screenshots_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute() and path.exists():
        return path
    return screenshots_dir / path.name


def ensure_hardlink(src: Path, dst: Path) -> bool:
    if not src.exists():
        raise FileNotFoundError(f"screen screenshot not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if os.path.samefile(src, dst):
            return False
        raise RuntimeError(
            f"refusing to overwrite existing non-hardlinked screenshot: {dst}"
        )

    try:
        os.link(src, dst)
    except OSError as exc:
        raise RuntimeError(
            "failed to hardlink screenshot; not falling back to copy because that "
            f"can duplicate the screenshot corpus: {src} -> {dst}: {exc}"
        ) from exc
    return True


def normalize_event_screenshot(
    repo: Path,
    event: dict,
    screenshots_dir: Path,
) -> bool:
    if event.get("connector") != "screen":
        return False

    source = event.get("source")
    if not isinstance(source, dict):
        return False

    raw_path = source.get("screenshot_path")
    if not isinstance(raw_path, str) or not raw_path:
        return False

    filename = Path(raw_path).name
    relative_path = f"{SCREENSHOTS_DIR}/{filename}"
    source["screenshot_path"] = relative_path
    return ensure_hardlink(
        screenshot_source_path(raw_path, screenshots_dir),
        repo / relative_path,
    )


def emit_data(stream, payload: bytes) -> None:
    stream.write(f"data {len(payload)}\n".encode())
    stream.write(payload)
    stream.write(b"\n")


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def fast_import_events(repo: Path, events_iter,
                       buffers: dict[str, dict[str, bytearray]],
                       parent_branch_exists: bool, total: int,
                       progress_every: int,
                       screenshots_dir: Path) -> tuple[int, dict[str, float]]:
    """Stream commits to git fast-import. Returns (count, last_ts_per_connector)."""
    proc = subprocess.Popen(
        ["git", "-C", str(repo), "fast-import", "--quiet", "--date-format=raw"],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    s = proc.stdin

    n = 0
    blob_mark = 0
    last_ts: dict[str, float] = {}
    per_connector_n: Counter = Counter()
    screenshot_links = 0
    has_parent = parent_branch_exists
    start = time.monotonic()

    try:
        for event in events_iter:
            if normalize_event_screenshot(repo, event, screenshots_dir):
                screenshot_links += 1
            connector = event["connector"]
            day = day_key(event["ts"])
            buf = buffers[connector].setdefault(day, bytearray())
            line = (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
            buf += line
            buffers[connector][day] = buf

            blob_mark += 1
            s.write(b"blob\n")
            s.write(f"mark :{blob_mark}\n".encode())
            emit_data(s, bytes(buf))

            ts_int = int(event["ts"])
            offset = local_tz_offset(event["ts"])
            ts_iso_local = local_iso(event["ts"])
            text_preview = event.get("text", "").replace("\n", " ")[:60]
            msg = f"{connector} @ {ts_iso_local}: {text_preview}".encode("utf-8")

            s.write(b"commit refs/heads/main\n")
            s.write(
                f"author indexer <indexer@local> {ts_int} {offset}\n".encode()
            )
            s.write(
                f"committer indexer <indexer@local> {ts_int} {offset}\n".encode()
            )
            emit_data(s, msg)
            if has_parent:
                s.write(b"from refs/heads/main^0\n")
                has_parent = False  # subsequent commits chain implicitly
            s.write(
                f"M 100644 :{blob_mark} {out_path(connector, event['ts'])}\n".encode()
            )
            s.write(b"\n")

            last_ts[connector] = event["ts"]
            per_connector_n[connector] += 1
            n += 1
            if n % progress_every == 0:
                elapsed = time.monotonic() - start
                rate = n / elapsed if elapsed > 0 else 0
                pct = (n / total * 100) if total else 0
                eta = (total - n) / rate if rate > 0 else 0
                log(
                    f"  [{n:>6}/{total}  {pct:5.1f}%]  ts={ts_iso_local}  "
                    f"rate={rate:6.1f}/s  elapsed={fmt_duration(elapsed)}  "
                    f"eta={fmt_duration(eta)}"
                )

        log("  flushing fast-import (writing packfile)...")
        s.close()
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"git fast-import exited {rc}")
    except Exception:
        proc.kill()
        raise

    elapsed = time.monotonic() - start
    log(f"  fast-import done: {n} commits in {fmt_duration(elapsed)} "
        f"({n / elapsed if elapsed > 0 else 0:.1f}/s)")
    log(f"  per-connector: {dict(per_connector_n)}")
    log(f"  screenshot hardlinks created: {screenshot_links}")

    return n, last_ts


def write_root_commit(repo: Path) -> None:
    """Create the initial root commit (only files: .gitignore + per-connector dirs)."""
    proc = subprocess.Popen(
        ["git", "-C", str(repo), "fast-import", "--quiet", "--date-format=raw"],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    s = proc.stdin

    gitignore = b".indexer-cursor.json\n/screenshots/\n"
    s.write(b"blob\nmark :1\n")
    emit_data(s, gitignore)

    s.write(b"blob\nmark :2\n")
    emit_data(s, b"")

    ts_int = int(CUTOVER_TS - 1)
    offset = local_tz_offset(CUTOVER_TS - 1)
    msg = b"init: empty index, cutover anchor"
    s.write(b"commit refs/heads/main\n")
    s.write(f"author indexer <indexer@local> {ts_int} {offset}\n".encode())
    s.write(f"committer indexer <indexer@local> {ts_int} {offset}\n".encode())
    emit_data(s, msg)
    s.write(b"M 100644 :1 .gitignore\n")
    for c in CONNECTORS:
        s.write(f"M 100644 :2 {c}/.gitkeep\n".encode())
    s.write(b"\n")

    s.close()
    rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"git fast-import exited {rc}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--logs-indexed-dir",
        type=Path,
        default=Path(os.environ.get("LOGS_INDEXED_DIR", str(DEFAULT_LOGS_INDEXED))),
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=Path(os.environ.get("STAGING_DIR", str(DEFAULT_STAGING))),
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--progress-every", type=int, default=1000,
                        help="Log progress every N commits (default 1000).")
    parser.add_argument(
        "--screen-screenshots-dir",
        type=Path,
        default=Path(
            os.environ.get("SCREEN_SCREENSHOTS_DIR", str(DEFAULT_SCREENSHOTS_DIR))
        ),
        help="Directory containing source screen PNGs to hardlink into logs-indexed/screenshots.",
    )
    args = parser.parse_args()

    repo = args.logs_indexed_dir
    staging = args.staging_dir
    screenshots_dir = args.screen_screenshots_dir

    init_repo(repo)
    branch_exists = bool(
        run_git(["rev-parse", "--quiet", "--verify", "refs/heads/main"], repo, check=False)
    )
    if not branch_exists:
        log("creating root commit (cutover anchor)...")
        write_root_commit(repo)
        run_git(["checkout", "main"], repo)
        branch_exists = True

    cursor = load_cursor(repo)
    log(f"repo:    {repo}")
    log(f"staging: {staging}")
    log(f"screenshots: {screenshots_dir}")
    log(f"cursor:  {cursor}")

    log("counting pending events per connector...")
    pending = count_pending(staging, cursor)
    total = sum(pending.values())
    if args.limit:
        total = min(total, args.limit)
    log(f"pending: total={total}  per-connector={dict(pending)}")
    if total == 0:
        log("nothing to do.")
        return

    buffers = load_existing_buffers(repo)

    events = merged_events(staging, cursor)
    if args.limit:
        events = (e for i, e in enumerate(events) if i < args.limit)

    log(f"streaming commits (progress every {args.progress_every})...")
    n, last_ts = fast_import_events(
        repo, events, buffers,
        parent_branch_exists=True,
        total=total,
        progress_every=args.progress_every,
        screenshots_dir=screenshots_dir,
    )

    # Sync working tree to new HEAD (fast-import only updates refs)
    log("syncing working tree (git reset --hard main)...")
    run_git(["reset", "--hard", "main"], repo)

    # Update cursor (preserve previous values for connectors with no new events)
    cursor.update(last_ts)
    save_cursor(repo, cursor)

    log(f"done: {n} new commits. final cursor: {cursor}")


if __name__ == "__main__":
    main()
