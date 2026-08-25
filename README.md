# Bangers Discovery Pipeline

Discovery, QA generation, and training JSONL export.

## Stages

```text
01_q_only   Generic interval QA cache
02_goals    Interval goals, combined goals, and bridge goals
03_bangers  Banger inputs, banger generation, combined manifest, and seed ranking
04_b_to_q   Discovery questions from bangers
05_q_to_b   Pre-banger questions from ranked bangers
```

## Options

```bash
scripts/runners/start_discovery.sh --help
```
