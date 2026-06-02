# Bangers Discovery Pipeline

Minimal runner for discovery, QA generation, and training JSONL export.

## Full Run

```bash
scripts/runners/start_discovery.sh \
  --provider codex \
  --interval-minutes 15 \
  --jobs 4
```

Use `--provider claude` to run with Claude. `--jobs` controls parallel model
calls for stages that support concurrency.

Stage 04 question generation samples 20% of selected banger opportunities by
default to control model usage. Pass `--questions-sample-fraction 1.0` to
generate questions for every selected banger opportunity, or
`--questions-sample-seed <seed>` to pick a different deterministic subset.
Pre-banger QA similarly samples 20% of selected ranked seeds by default,
stratified across the ranking; use `--seed-sample-fraction 1.0` or
`--seed-sample-seed <seed>` to override it.

## Day Shards

Use `--day` or `--days`. The selector is zero-based and inclusive:

- `--day 0` runs the first day in the interval file.
- `--day 1` runs the second day.
- `--day 1-5` runs days 1, 2, 3, 4, and 5.

Run `python scripts/print_day_intervals.py` to print each day selector, date, interval count, and interval index range.

Run interval-stage shards in parallel:

```bash
scripts/runners/start_discovery.sh --phase setup

scripts/runners/start_discovery.sh --phase interval --day 0 --jobs 4
scripts/runners/start_discovery.sh --phase interval --day 1 --jobs 4
scripts/runners/start_discovery.sh --phase interval --day 2 --jobs 4
```

After those finish, run day-scoped aggregate discovery for each completed day:

```bash
scripts/runners/start_discovery.sh --phase aggregate --day 0 --jobs 4
scripts/runners/start_discovery.sh --phase aggregate --day 1 --jobs 4
scripts/runners/start_discovery.sh --phase aggregate --day 2 --jobs 4
```

Each day writes into its own scoped directories, so day 1 banger files do not
invalidate or overwrite day 0 banger files. A final no-day aggregate still builds
the cross-day global aggregate from all day-scoped goal files:

```bash
scripts/runners/start_discovery.sh --phase aggregate --jobs 4
```

Then run pre-banger QA shards in parallel:

```bash
scripts/runners/start_discovery.sh --phase pre-banger --day 0 --jobs 4
scripts/runners/start_discovery.sh --phase pre-banger --day 1 --jobs 4
scripts/runners/start_discovery.sh --phase pre-banger --day 2 --jobs 4
```

Day-scoped outputs are stored under day range directories:

```text
01_goals/days_0/goal_*.json
02a_combined/days_0/combined.json
02b_bridges/days_0/bridges.json
02c_suggestion_inputs/days_0/inputs.json
03_bangers/days_0/bangers_*.json
04_questions/days_0/final_questions.json
10_generic_qa/days_0/final_qa.json
20_pre_banger_qa/days_0/seed_rankings.json
20_pre_banger_qa/days_0/final_qa.json
```

## Options

```bash
scripts/runners/start_discovery.sh --help
```

## Inspect

```bash
uv run scripts/serve_discovery_viewer.py --discovery-dir discovery_codex_15m
```
