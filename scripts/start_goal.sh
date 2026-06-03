RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"

bash scripts/runners/start_discovery.sh \
  --phase 02_goals \
  --interval-range 0-125 \
  --run-id "$RUN_ID" \
  --jobs 4

bash scripts/runners/start_discovery.sh \
  --phase 03_bangers \
  --interval-range 0-125 \
  --run-id "$RUN_ID" \
  --jobs 4