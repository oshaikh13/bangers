from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def load_template(path: Path, required_placeholders: Iterable[str]) -> str:
    if not path.exists():
        raise SystemExit(f"prompt template not found: {path}")

    template = path.read_text(encoding="utf-8")
    for placeholder in required_placeholders:
        if placeholder not in template:
            raise SystemExit(f"template missing {placeholder} placeholder: {path}")
    return template


def render_discovery_prompt(
    template: str,
    row: dict[str, Any],
    goal_path: Path,
    provider: str,
) -> str:
    interval_index = row.get("interval_index")
    if interval_index is None:
        raise SystemExit(f"row is missing interval_index: {row}")

    candidate_row = json.dumps(row, ensure_ascii=False, sort_keys=True)
    rendered = (
        template.replace("{candidate_row}", candidate_row)
        .replace("{interval_index}", str(interval_index))
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(goal_path)
        + "\n"
    )


def render_combine_prompt(
    template: str,
    goals_dir: Path,
    combined_path: Path,
    provider: str,
) -> str:
    rendered = (
        template.replace("{dir_name}", str(goals_dir))
        .replace("{combined_path}", str(combined_path))
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(combined_path)
        + "\n"
    )


def render_bridges_prompt(
    template: str,
    combined_path: Path,
    bridges_path: Path,
    provider: str,
) -> str:
    rendered = (
        template.replace("{combined_path}", str(combined_path))
        .replace("{bridges_path}", str(bridges_path))
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(bridges_path)
        + "\n"
    )


def render_bangers_prompt(
    template: str,
    combined_json_element: dict[str, Any],
    bangers_path: Path,
    provider: str,
) -> str:
    rendered = template.replace(
        "{combined_json_element}",
        json.dumps(combined_json_element, ensure_ascii=False, sort_keys=True),
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(bangers_path)
        + "\n"
    )


def render_bangers_batch_prompt(
    template: str,
    batch_elements: list[dict[str, Any]],
    provider: str,
) -> str:
    return template.replace(
        "{combined_json_element}",
        json.dumps(batch_elements, ensure_ascii=False, sort_keys=True),
    )


def render_questions_prompt(
    template: str,
    suggestion_json: dict[str, Any],
    questions_path: Path,
    provider: str,
) -> str:
    rendered = template.replace(
        "{suggestion_json}",
        json.dumps(suggestion_json, ensure_ascii=False, sort_keys=True),
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(questions_path)
        + "\n"
    )
