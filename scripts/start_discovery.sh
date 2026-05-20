uv run scripts/run_discovery_goals.py --provider codex --interval-indexes 0-1 --jobs 2
uv run scripts/run_discovery_combine.py --provider codex --force
uv run scripts/run_discovery_bangers.py --provider codex --jobs 2
uv run scripts/run_discovery_questions.py --provider codex --jobs 2
