#!/usr/bin/env bash
set -euo pipefail

provider="codex"
interval_minutes="15"
interval_range=""
run_id=""
jobs="4"
phase="all"
banger_batch_size="5"
skip_setup="false"
effort="high"
force="false"

usage() {
  cat <<'EOF'
Usage:
  scripts/runners/start_discovery.sh --interval-range START-END [options]

Options:
  --provider codex|claude       Provider to use. Default: codex
  --interval-minutes N          Interval size. Default: 15
  --interval-range START-END    Inclusive interval index range, e.g. 0-42
  --run-id ID                   Versioned run id. Defaults to new for 02/all, latest otherwise
  --jobs N                      Parallel model calls where supported. Default: 4
  --phase NAME                  all, setup, 01_q_only, 02_goals, 03_bangers,
                                04_b_to_q, 05_q_to_b. Default: all
  --banger-batch-size N         Batch size for banger generation. Default: 5
  --effort LEVEL                Reasoning effort for model stages. Default: high
  --force                       Rerun stages even when their outputs exist
  --skip-setup                  Skip uv sync, indexing, and interval recording
  -h, --help                    Show this help

Phases:
  all         Setup, 01_q_only, 02_goals, 03_bangers, 04_b_to_q, and 05_q_to_b
  setup       uv sync, indexing, and interval recording
  01_q_only   Generic interval QA cache
  02_goals    Interval goals, combined goals, and bridge goals
  03_bangers  Banger inputs, banger generation, manifest, and seed ranking
  04_b_to_q   Discovery questions from bangers
  05_q_to_b   Pre-banger questions from ranked bangers
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
    --interval-range)
      interval_range="$2"
      shift 2
      ;;
    --run-id)
      run_id="$2"
      shift 2
      ;;
    --jobs)
      jobs="$2"
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
    --force)
      force="true"
      shift
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
  all|setup|01_q_only|02_goals|03_bangers|04_b_to_q|05_q_to_b) ;;
  *)
    echo "invalid --phase: $phase" >&2
    usage >&2
    exit 2
    ;;
esac

if [[ "$phase" != "setup" && -z "$interval_range" ]]; then
  echo "--interval-range is required for phase $phase" >&2
  usage >&2
  exit 2
fi

discovery_dir="discovery_${provider}_${interval_minutes}m"
scope_slug="intervals_${interval_range}"
run_root=""

effort_args=()
if [[ -n "$effort" ]]; then
  case "$provider" in
    codex) effort_args=(--codex-reasoning-effort "$effort") ;;
    claude) effort_args=(--claude-effort "$effort") ;;
  esac
fi

run_args=()
if [[ "$phase" != "setup" ]]; then
  run_args=(--interval-range "$interval_range")
fi

run_stage() {
  local runner="$1"
  shift
  local cmd=(uv run "$runner" "$@")
  if [[ "$force" == "true" ]]; then
    cmd+=(--force)
  fi
  "${cmd[@]}"
}

resolve_run_root() {
  if [[ -n "$run_root" || "$phase" == "setup" ]]; then
    return
  fi

  local selected_run_id="$run_id"
  if [[ -z "$selected_run_id" ]]; then
    case "$phase" in
      all|02_goals)
        selected_run_id="$(date -u +%Y%m%dT%H%M%SZ)"
        ;;
      *)
        local scope_dir="$discovery_dir/$scope_slug"
        if [[ ! -d "$scope_dir" ]]; then
          echo "no runs found for $scope_slug under $discovery_dir" >&2
          exit 2
        fi
        selected_run_id="$(find "$scope_dir" -mindepth 1 -maxdepth 1 -type d -print | sort | tail -1 | xargs basename)"
        if [[ -z "$selected_run_id" ]]; then
          echo "no runs found for $scope_slug under $discovery_dir" >&2
          exit 2
        fi
        ;;
    esac
  fi

  run_id="$selected_run_id"
  run_root="$discovery_dir/$scope_slug/$run_id"
  echo "using run root: $run_root" >&2
}

run_setup() {
  if [[ "$skip_setup" == "true" ]]; then
    return
  fi
  uv sync
  ./scripts/index_all.sh
  uv run scripts/record_intervals.py "$interval_minutes"
}

run_q_only() {
  run_stage scripts/runners/run_generic_qa.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${run_args[@]}" \
    "${effort_args[@]}" \
    --qa-types all \
    --jobs "$jobs" \
    --continue-on-error

  local dir="$discovery_dir/01_q_only/$scope_slug"
  uv run scripts/export_training_questions.py \
    --input "$dir/final_qa.json" \
    --output "$dir/training_questions.jsonl"
}

run_goals() {
  resolve_run_root
  run_stage scripts/runners/run_discovery_goals.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${run_args[@]}" \
    --run-root "$run_root" \
    "${effort_args[@]}" \
    --jobs "$jobs" \
    --continue-on-error

  run_stage scripts/runners/run_discovery_combine.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${run_args[@]}" \
    --run-root "$run_root" \
    "${effort_args[@]}"

  run_stage scripts/runners/run_discovery_bridges.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${run_args[@]}" \
    --run-root "$run_root" \
    "${effort_args[@]}"
}

run_bangers() {
  resolve_run_root
  run_stage scripts/build_suggestion_inputs.py \
    --discovery-dir "$discovery_dir" \
    "${run_args[@]}" \
    --run-root "$run_root"

  run_stage scripts/runners/run_discovery_bangers.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${run_args[@]}" \
    --run-root "$run_root" \
    "${effort_args[@]}" \
    --jobs "$jobs" \
    --banger-batch-size "$banger_batch_size" \
    --continue-on-error

  run_stage scripts/combine_bangers.py \
    --discovery-dir "$discovery_dir" \
    "${run_args[@]}" \
    --run-root "$run_root"

  run_stage scripts/runners/run_banger_ranking.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${run_args[@]}" \
    --run-root "$run_root" \
    "${effort_args[@]}"
}

run_b_to_q() {
  resolve_run_root
  run_stage scripts/runners/run_discovery_questions.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${run_args[@]}" \
    --run-root "$run_root" \
    "${effort_args[@]}" \
    --jobs "$jobs" \
    --continue-on-error

  uv run scripts/export_training_questions.py \
    --input "$run_root/04_b_to_q/final_questions.json" \
    --output "$run_root/04_b_to_q/training_questions.jsonl"
}

run_q_to_b() {
  resolve_run_root
  run_stage scripts/runners/run_pre_banger_qa.py \
    --provider "$provider" \
    --interval-minutes "$interval_minutes" \
    "${run_args[@]}" \
    --run-root "$run_root" \
    "${effort_args[@]}" \
    --qa-types all \
    --jobs "$jobs" \
    --continue-on-error

  uv run scripts/export_training_questions.py \
    --input "$run_root/05_q_to_b/final_qa.json" \
    --output "$run_root/05_q_to_b/training_questions.jsonl"
}

case "$phase" in
  all)
    run_setup
    run_q_only
    run_goals
    run_bangers
    run_b_to_q
    run_q_to_b
    ;;
  setup)
    run_setup
    ;;
  01_q_only)
    run_q_only
    ;;
  02_goals)
    run_goals
    ;;
  03_bangers)
    run_bangers
    ;;
  04_b_to_q)
    run_b_to_q
    ;;
  05_q_to_b)
    run_q_to_b
    ;;
esac
