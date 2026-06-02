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

After those finish, run the aggregate discovery stages once:

```bash
scripts/runners/start_discovery.sh --phase aggregate --jobs 4
```

Then run pre-banger QA shards in parallel:

```bash
scripts/runners/start_discovery.sh --phase pre-banger --day 0 --jobs 4
scripts/runners/start_discovery.sh --phase pre-banger --day 1 --jobs 4
scripts/runners/start_discovery.sh --phase pre-banger --day 2 --jobs 4
```

Day-scoped outputs are named by day range:

```text
10_generic_qa/final_qa_days_0.json
20_pre_banger_qa/seed_rankings_days_0.json
20_pre_banger_qa/final_qa_days_0.json
```

## Options

```bash
scripts/runners/start_discovery.sh --help
```

## Inspect

```bash
uv run scripts/serve_discovery_viewer.py --discovery-dir discovery_codex_15m
```
