#!/usr/bin/env bash
set -euo pipefail

provider="codex"
interval_minutes="15"
jobs="4"
phase="all"
day_selector=""
banger_batch_size="5"
skip_setup="false"
effort=""

usage() {
  cat <<'EOF'
Usage:
  scripts/runners/start_discovery.sh [options]

Options:
  --provider codex|claude       Provider to use. Default: codex
  --interval-minutes N          Interval size. Default: 15
  --jobs N                      Parallel model calls where supported. Default: 4
  --day RANGE, --days RANGE     Zero-based day selector, e.g. 0 or 1-5
  --phase NAME                  all, setup, interval, aggregate, qa, pre-banger. Default: all
  --banger-batch-size N         Batch size for banger generation. Default: 5
  --effort LEVEL                Reasoning effort for model stages. Maps to the
                                provider flag: codex --codex-reasoning-effort
                                (freeform, default high), claude --claude-effort
                                (low|medium|high|xhigh|max). Default: runner default.
  --skip-setup                  Skip uv sync, indexing, and interval recording
  -h, --help                    Show this help

Phases:
  all         Setup, interval discovery, aggregate discovery, QA, and pre-banger QA
  setup       uv sync, indexing, and interval recording
  interval    Discovery goals and generic QA for the selected interval/day shard
  aggregate   Combine, bridges, suggestion inputs, bangers, questions, and export
  qa          Generic QA only
  pre-banger  Pre-banger QA only
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --provider)
      provider="$2"
      shift 2
      ;;
    --interval-minutes)
      interval_minutes="$2"
      shift 2
      ;;
    --jobs)
      jobs="$2"
      shift 2
      ;;
    --day|--days)
      day_selector="$2"
      shift 2
      ;;
    --phase)
      phase="$2"
      shift 2
      ;;
    --banger-batch-size)
      banger_batch_size="$2"
      shift 2
      ;;
    --effort)
      effort="$2"
      shift 2
      ;;
    --skip-setup)
      skip_setup="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$phase" in
  all|setup|interval|aggregate|qa|pre-banger) ;;
  *)
    echo "invalid --phase: $phase" >&2
    usage >&2
    exit 2
    ;;
esac

discovery_dir="discovery_${provider}_${interval_minutes}m"
day_args=()
day_suffix=""
scope_slug="global"
if [[ -n "$day_selector" ]]; then
  day_args=(--day "$day_selector")
  day_suffix="${day_selector//,/_}"
  day_suffix="${day_suffix// /}"
  scope_slug="days_${day_suffix}"
fi

effort_args=()
if [[ -n "$effort" ]]; then
  case "$provider" in
    codex) effort_args=(--codex-reasoning-effort "$effort") ;;
    claude) effort_args=(--claude-effort "$effort") ;;
  esac
fi

stage_dir() {
  local stage="$1"
  if [[ "$scope_slug" == "global" ]]; then
    printf '%s/%s' "$discovery_dir" "$stage"
  else
    printf '%s/%s/%s' "$discovery_dir" "$stage" "$scope_slug"
  fi
}

run_setup() {
  if [[ "$skip_setup" == "true" ]]; then
    return
  fi
  uv sync
  ./scripts/index_all.sh
  uv run scripts/record_intervals.py "$interval_minutes"
}

run_interval_discovery() {
  uv run scripts/runners/run_discovery_goals.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${day_args[@]}" \
    "${effort_args[@]}" \
    --jobs "$jobs" \
    --continue-on-error
}

run_aggregate_discovery() {
  uv run scripts/runners/run_discovery_combine.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${day_args[@]}" \
    "${effort_args[@]}" \
    --force

  uv run scripts/runners/run_discovery_bridges.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${day_args[@]}" \
    "${effort_args[@]}" \
    --force

  uv run scripts/build_suggestion_inputs.py \
    --discovery-dir "$discovery_dir" \
    "${day_args[@]}"

  uv run scripts/runners/run_discovery_bangers.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${day_args[@]}" \
    "${effort_args[@]}" \
    --jobs "$jobs" \
    --banger-batch-size "$banger_batch_size" \
    --continue-on-error

  uv run scripts/combine_bangers.py \
    --discovery-dir "$discovery_dir" \
    "${day_args[@]}"

  uv run scripts/runners/run_discovery_questions.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${day_args[@]}" \
    "${effort_args[@]}" \
    --jobs "$jobs" \
    --continue-on-error

  uv run scripts/export_training_questions.py \
    --input "$(stage_dir 04_questions)/final_questions.json" \
    --output "$(stage_dir 04_questions)/training_questions.jsonl"
}

run_generic_qa() {
  uv run scripts/runners/run_generic_qa.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${day_args[@]}" \
    "${effort_args[@]}" \
    --qa-types all \
    --jobs "$jobs" \
    --continue-on-error

  local input="$(stage_dir 10_generic_qa)/final_qa.json"
  local output="$(stage_dir 10_generic_qa)/training_questions.jsonl"

  uv run scripts/export_training_questions.py \
    --input "$input" \
    --output "$output"
}

run_pre_banger_qa() {
  uv run scripts/runners/run_pre_banger_qa.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${day_args[@]}" \
    "${effort_args[@]}" \
    --qa-types all \
    --jobs "$jobs" \
    --continue-on-error

  local input="$(stage_dir 20_pre_banger_qa)/final_qa.json"
  local output="$(stage_dir 20_pre_banger_qa)/training_questions.jsonl"

  uv run scripts/export_training_questions.py \
    --input "$input" \
    --output "$output"
}

case "$phase" in
  all)
    run_setup
    run_interval_discovery
    run_aggregate_discovery
    run_generic_qa
    run_pre_banger_qa
    ;;
  setup)
    run_setup
    ;;
  interval)
    run_interval_discovery
    run_generic_qa
    ;;
  aggregate)
    run_aggregate_discovery
    ;;
  qa)
    run_generic_qa
    ;;
  pre-banger)
    run_pre_banger_qa
    ;;
esac
