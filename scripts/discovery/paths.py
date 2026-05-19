from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTERVAL_MINUTES = 15
DEFAULT_DISCOVERY_KIND = "goals"
DEFAULT_DISCOVERY_TEMPLATES = {
    "goals": REPO_ROOT / "prompts" / "discovery_goals.md",
    "suggestions": REPO_ROOT / "prompts" / "discovery_suggestions.md",
}
DEFAULT_COMBINE_TEMPLATE = REPO_ROOT / "prompts" / "combine.md"
DEFAULT_QUESTIONS_TEMPLATE = REPO_ROOT / "prompts" / "discovery_questions.md"


def default_intervals_path(interval_minutes: int) -> Path:
    return REPO_ROOT / "data" / f"log_intervals_{interval_minutes}m.jsonl"


def default_candidates_dir(
    provider: str,
    interval_minutes: int,
    discovery_kind: str = DEFAULT_DISCOVERY_KIND,
) -> Path:
    return REPO_ROOT / f"candidates_{provider}_{discovery_kind}_{interval_minutes}m"
