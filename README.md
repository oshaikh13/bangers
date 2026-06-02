# Bangers Discovery Pipeline

Minimal commands to build indexed logs, create interval rows, run discovery,
generate QA data, and export training JSONL.

## Run

Prereqs: Python 3.11+, `uv`, and either `codex` or `claude` on `PATH`.
Source logs default to `../powernap/logs`.
Commands below use 4 parallel provider jobs where supported.

```bash
uv sync

export PROVIDER=codex
export INTERVAL=15
export DISCOVERY_DIR="discovery_${PROVIDER}_${INTERVAL}m"

./scripts/index_all.sh
uv run scripts/record_intervals.py "$INTERVAL"

uv run scripts/runners/run_discovery_goals.py \
  --provider "$PROVIDER" \
  --interval-minutes "$INTERVAL" \
  --jobs 4 \
  --continue-on-error

uv run scripts/runners/run_discovery_combine.py \
  --provider "$PROVIDER" \
  --interval-minutes "$INTERVAL" \
  --force

uv run scripts/runners/run_discovery_bridges.py \
  --provider "$PROVIDER" \
  --interval-minutes "$INTERVAL" \
  --force

uv run scripts/build_suggestion_inputs.py \
  --discovery-dir "$DISCOVERY_DIR"

uv run scripts/runners/run_discovery_bangers.py \
  --provider "$PROVIDER" \
  --interval-minutes "$INTERVAL" \
  --jobs 4 \
  --banger-batch-size 5 \
  --continue-on-error

uv run scripts/combine_bangers.py \
  --discovery-dir "$DISCOVERY_DIR"

uv run scripts/runners/run_discovery_questions.py \
  --provider "$PROVIDER" \
  --interval-minutes "$INTERVAL" \
  --jobs 4 \
  --continue-on-error

uv run scripts/export_training_questions.py \
  --input "$DISCOVERY_DIR/04_questions/final_questions.json" \
  --output "$DISCOVERY_DIR/04_questions/training_questions.jsonl"

uv run scripts/runners/run_generic_qa.py \
  --provider "$PROVIDER" \
  --interval-minutes "$INTERVAL" \
  --qa-types all \
  --jobs 4 \
  --continue-on-error

uv run scripts/export_training_questions.py \
  --input "$DISCOVERY_DIR/10_generic_qa/final_qa.json" \
  --output "$DISCOVERY_DIR/10_generic_qa/training_questions.jsonl"

uv run scripts/runners/run_pre_banger_qa.py \
  --provider "$PROVIDER" \
  --interval-minutes "$INTERVAL" \
  --qa-types all \
  --jobs 4 \
  --continue-on-error

uv run scripts/export_training_questions.py \
  --input "$DISCOVERY_DIR/20_pre_banger_qa/final_qa.json" \
  --output "$DISCOVERY_DIR/20_pre_banger_qa/training_questions.jsonl"
```

Use `PROVIDER=claude` to run with Claude instead of Codex.
For pipeline 20, `--qa-types all` runs the default non-overlapping set:
`timing,curiosity,disregard,value,threaded`. The `value` type asks for a
continuous 1 to 100 estimate of how worthwhile proactive help would be. The
`threaded` type is a multi-turn shape built from timing, curiosity, and
self-done arcs, not a separate semantic category.
Pipeline 20 groups banger seeds by UTC day, ranks each day's concatenated
suggestions in parallel using `--jobs`, then writes a stitched
`seed_rankings.json`. Interval selectors only filter which already-ranked seeds
get QA generated. The ranker reads daily files derived from
`$DISCOVERY_DIR/03_bangers/combined_bangers.json`, which is written by
`scripts/combine_bangers.py` and refreshed by pipeline 20 before ranking.

## Shard Large Runs

For a smaller or parallel shard, add the same day or interval selector to
interval-based stages. `--days` is zero-based and derived from interval row start
dates:

```bash
export DAYS=0-4

uv run scripts/runners/run_discovery_goals.py --provider "$PROVIDER" --interval-minutes "$INTERVAL" --days "$DAYS" --jobs 4
uv run scripts/runners/run_generic_qa.py --provider "$PROVIDER" --interval-minutes "$INTERVAL" --days "$DAYS" --qa-types all --jobs 4
uv run scripts/runners/run_pre_banger_qa.py --provider "$PROVIDER" --interval-minutes "$INTERVAL" --days "$DAYS" --qa-types all --jobs 4
```

Then run the combine, bridge, suggestion-input, banger, question, and export
commands from the main block after the relevant shards finish.

## Inspect

```bash
uv run scripts/serve_discovery_viewer.py --discovery-dir "$DISCOVERY_DIR"
```
