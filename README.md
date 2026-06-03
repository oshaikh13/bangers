# Bangers Discovery Pipeline

Minimal runner for discovery, QA generation, and training JSONL export.

## Full Run

```bash
scripts/runners/start_discovery.sh \
  --provider codex \
  --interval-minutes 15 \
  --interval-range 0-42 \
  --jobs 4
```

Use `--provider claude` to run with Claude. `--jobs` controls parallel model
calls for stages that support concurrency. `--interval-range START-END` is
inclusive and is the canonical scope selector.

## Stages

```text
01_q_only   Generic interval QA cache
02_goals    Interval goals, combined goals, and bridge goals
03_bangers  Banger inputs, banger generation, combined manifest, and seed ranking
04_b_to_q   Discovery questions from bangers
05_q_to_b   Pre-banger questions from ranked bangers
```

`01_q_only` is reusable cache output. The remaining stages run under a
versioned run root. If `--run-id` is omitted, `02_goals` and `all` create a new
timestamp run id, while downstream phases use the latest run for the interval
range.

## Example

```bash
scripts/runners/start_discovery.sh --phase setup
scripts/runners/start_discovery.sh --phase 01_q_only --interval-range 0-42 --jobs 4
scripts/runners/start_discovery.sh --phase 02_goals --interval-range 0-42 --jobs 4
scripts/runners/start_discovery.sh --phase 03_bangers --interval-range 0-42 --jobs 4
scripts/runners/start_discovery.sh --phase 04_b_to_q --interval-range 0-42 --jobs 4
scripts/runners/start_discovery.sh --phase 05_q_to_b --interval-range 0-42 --jobs 4
```

Outputs are stored under:

```text
discovery_codex_15m/
  01_q_only/intervals_0-42/final_qa.json
  intervals_0-42/RUN_ID/manifest.json
  intervals_0-42/RUN_ID/02_goals/goals/goal_*.json
  intervals_0-42/RUN_ID/02_goals/combined/combined.json
  intervals_0-42/RUN_ID/02_goals/bridges/bridges.json
  intervals_0-42/RUN_ID/03_bangers/inputs.json
  intervals_0-42/RUN_ID/03_bangers/combined_bangers.json
  intervals_0-42/RUN_ID/03_bangers/seed_rankings.json
  intervals_0-42/RUN_ID/04_b_to_q/final_questions.json
  intervals_0-42/RUN_ID/05_q_to_b/final_qa.json
```

## Sampling

`04_b_to_q` samples 10% of generated banger opportunities by default using
seed `0`. `03_bangers` ranks all generated banger seeds, and `05_q_to_b`
samples a separate stratified 10% subset using seed `0`.

Use `--questions-sample-fraction 1.0` for all `04_b_to_q` bangers, or
`--seed-sample-fraction 1.0` for all `05_q_to_b` ranked seeds.

## Prompts

Prompts live in folders matching the stage names:

```text
prompts/01_q_only/
prompts/02_goals/
prompts/03_bangers/
prompts/04_b_to_q/
prompts/05_q_to_b/
```

## Options

```bash
scripts/runners/start_discovery.sh --help
```

## Inspect

```bash
uv run scripts/serve_discovery_viewer.py --discovery-dir discovery_codex_15m
```
