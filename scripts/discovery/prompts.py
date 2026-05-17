from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_template(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"prompt template not found: {path}")

    template = path.read_text(encoding="utf-8")
    if "{candidate_row}" not in template:
        raise SystemExit(f"template missing {{candidate_row}} placeholder: {path}")
    return template


def render_prompt(
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

