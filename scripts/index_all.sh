#!/usr/bin/env bash
# Run the three indexing steps in order:
#   1. normalize.py        — 5 non-audio connectors → staging/<connector>.jsonl
#   2. audio_to_jsonl.py   — audio .md → staging/audio.jsonl
#   3. index.py            — staging → logs-indexed/ git commits (incremental)
#
# Per-stage stdout/stderr is teed to data/index_logs/<UTC-timestamp>/<stage>.log.
# Override input/output locations via env vars (or pass --logs-dir etc. to scripts):
#   POWERNAP_LOGS_DIR   — where powernap connector logs live (default: ../powernap/logs)
#   STAGING_DIR         — intermediate normalized output  (default: staging/)
#   LOGS_INDEXED_DIR    — final git-indexed output         (default: logs-indexed/)

set -uo pipefail

cd "$(dirname "$0")/.."

LOG_DIR="data/index_logs/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$LOG_DIR"

run_stage() {
    local stage=$1; shift
    echo
    echo "=== $stage ==="
    "$@" 2>&1 | tee "$LOG_DIR/$stage.log"
}

run_stage "normalize" \
    uv run python src/indexing/normalize.py
run_stage "audio_to_jsonl" \
    uv run python src/indexing/audio_to_jsonl.py
run_stage "index" \
    uv run python src/indexing/index.py

echo
echo "=========== ALL DONE ==========="
echo "logs: $LOG_DIR"
