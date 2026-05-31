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
    batch_elements: Any,
    provider: str,
) -> str:
    del provider
    return template.replace(
        "{combined_json_element}",
        json.dumps(batch_elements, ensure_ascii=False, sort_keys=True),
    )


def render_questions_prompt(
    template: str,
    suggestion_json: dict[str, Any],
    context_events: list[dict[str, Any]],
    questions_path: Path,
    provider: str,
) -> str:
    rendered = (
        template.replace(
            "{suggestion_json}",
            json.dumps(suggestion_json, ensure_ascii=False, sort_keys=True),
        )
        .replace(
            "{context_events_json}",
            json.dumps(context_events, ensure_ascii=False, sort_keys=True),
        )
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(questions_path)
        + "\n"
    )


def render_generic_qa_prompt(
    template: str,
    qa_type: str,
    interval: dict[str, Any],
    context_events: list[dict[str, Any]],
    qa_path: Path,
    provider: str,
    pairs_per_run: int,
) -> str:
    timestamp_ts = interval.get("end_ts")
    timestamp_iso = interval.get("end_utc") or interval.get("end_local") or timestamp_ts
    rendered = (
        template.replace("{qa_type}", qa_type)
        .replace("{qa_timestamp}", str(timestamp_iso))
        .replace("{qa_timestamp_ts}", str(timestamp_ts))
        .replace(
            "{interval_json}",
            json.dumps(interval, ensure_ascii=False, sort_keys=True),
        )
        .replace(
            "{context_events_json}",
            json.dumps(context_events, ensure_ascii=False, sort_keys=True),
        )
        .replace("{pairs_per_run}", str(pairs_per_run))
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(qa_path)
        + "\n"
    )


def render_pre_banger_qa_prompt(
    template: str,
    qa_type: str,
    seed: dict[str, Any],
    context_events: list[dict[str, Any]],
    qa_path: Path,
    provider: str,
    pairs_per_run: int,
) -> str:
    rendered = (
        template.replace("{qa_type}", qa_type)
        .replace(
            "{seed_json}",
            json.dumps(seed, ensure_ascii=False, sort_keys=True),
        )
        .replace(
            "{context_events_json}",
            json.dumps(context_events, ensure_ascii=False, sort_keys=True),
        )
        .replace("{pairs_per_run}", str(pairs_per_run))
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(qa_path)
        + "\n"
    )


def render_pre_banger_seed_filter_prompt(
    template: str,
    seeds: list[dict[str, Any]],
    output_path: Path,
    provider: str,
) -> str:
    rendered = template.replace(
        "{banger_seeds_json}",
        json.dumps(seeds, ensure_ascii=False, sort_keys=True),
    )
    return (
        rendered
        + "\n\n"
        + f"For this {provider} run, write the JSON file to this exact path: "
        + str(output_path)
        + "\n"
    )
