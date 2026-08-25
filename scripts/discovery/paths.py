from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTERVAL_MINUTES = 15
DEFAULT_DISCOVERY_TEMPLATE = REPO_ROOT / "prompts" / "02_goals" / "goals.md"
DEFAULT_COMBINE_TEMPLATE = REPO_ROOT / "prompts" / "02_goals" / "combine.md"
DEFAULT_BRIDGES_TEMPLATE = REPO_ROOT / "prompts" / "02_goals" / "bridges.md"
DEFAULT_BANGERS_TEMPLATE = REPO_ROOT / "prompts" / "03_bangers" / "bangers.md"
DEFAULT_QUESTIONS_TEMPLATE = REPO_ROOT / "prompts" / "04_b_to_q" / "questions.md"
DEFAULT_GENERIC_QA_COMMON_TEMPLATE = (
    REPO_ROOT / "prompts" / "01_q_only" / "common.md"
)
DEFAULT_GENERIC_QA_PROMPTS_DIR = REPO_ROOT / "prompts" / "01_q_only"
DEFAULT_PRE_BANGER_QA_COMMON_TEMPLATE = (
    REPO_ROOT / "prompts" / "05_q_to_b" / "common.md"
)
DEFAULT_PRE_BANGER_SEED_FILTER_TEMPLATE = (
    REPO_ROOT / "prompts" / "03_bangers" / "rank_bangers.md"
)
DEFAULT_PRE_BANGER_QA_PROMPTS_DIR = REPO_ROOT / "prompts" / "05_q_to_b"


def default_intervals_path(interval_minutes: int) -> Path:
    return REPO_ROOT / "data" / f"log_intervals_{interval_minutes}m.jsonl"


def default_discovery_dir(
    provider: str,
    interval_minutes: int,
) -> Path:
    return REPO_ROOT / f"discovery_{provider}_{interval_minutes}m"
