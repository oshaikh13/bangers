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
    candidate_path: Path,
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
        + str(candidate_path)
        + "\n"
    )


def render_combine_prompt(
    template: str,
    candidates_dir: Path,
    provider: str,
) -> str:
    combined_path = candidates_dir / "combined.json"
    rendered = template.replace("{dir_name}", str(candidates_dir))
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(combined_path)
        + "\n"
    )


def render_questions_prompt(
    template: str,
    combined_json_element: dict[str, Any],
    questions_path: Path,
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
        + str(questions_path)
        + "\n"
    )
