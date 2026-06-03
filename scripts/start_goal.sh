#!/usr/bin/env bash
set -euo pipefail

provider="${PROVIDER:-codex}"
interval_minutes="${INTERVAL_MINUTES:-15}"
interval_range="${INTERVAL_RANGE:-0-125}"
jobs="${JOBS:-4}"
discovery_dir="discovery_${provider}_${interval_minutes}m"
scope_dir="${discovery_dir}/intervals_${interval_range}"

if [[ -z "${RUN_ID:-}" ]]; then
  if [[ -d "$scope_dir" ]] && find "$scope_dir" -mindepth 1 -maxdepth 1 -type d -print -quit | grep -q .; then
    RUN_ID="$(find "$scope_dir" -mindepth 1 -maxdepth 1 -type d -print | sort | tail -1 | xargs basename)"
  else
    RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
  fi
fi

echo "using run id: $RUN_ID"
echo "interval range: $interval_range"

run_cmd() {
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  if [[ "${DRY_RUN:-}" == "1" || "${DRY_RUN:-}" == "true" ]]; then
    return 0
  fi
  "$@"
}

run_cmd bash scripts/runners/start_discovery.sh \
  --provider "$provider" \
  --interval-minutes "$interval_minutes" \
  --phase 02_goals \
  --interval-range "$interval_range" \
  --run-id "$RUN_ID" \
  --jobs "$jobs"

run_cmd bash scripts/runners/start_discovery.sh \
  --provider "$provider" \
  --interval-minutes "$interval_minutes" \
  --phase 03_bangers \
  --interval-range "$interval_range" \
  --run-id "$RUN_ID" \
  --jobs "$jobs"
