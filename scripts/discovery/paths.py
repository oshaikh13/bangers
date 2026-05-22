from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTERVAL_MINUTES = 15
DEFAULT_DISCOVERY_TEMPLATE = REPO_ROOT / "prompts" / "01_discovery_goals.md"
DEFAULT_COMBINE_TEMPLATE = REPO_ROOT / "prompts" / "02a_discovery_combine.md"
DEFAULT_BRIDGES_TEMPLATE = REPO_ROOT / "prompts" / "02b_discovery_bridges.md"
DEFAULT_BANGERS_TEMPLATE = REPO_ROOT / "prompts" / "03_discovery_bangers.md"
DEFAULT_QUESTIONS_TEMPLATE = REPO_ROOT / "prompts" / "04_discovery_questions.md"


def default_intervals_path(interval_minutes: int) -> Path:
    return REPO_ROOT / "data" / f"log_intervals_{interval_minutes}m.jsonl"


def default_discovery_dir(
    provider: str,
    interval_minutes: int,
) -> Path:
    return REPO_ROOT / f"discovery_{provider}_{interval_minutes}m"
