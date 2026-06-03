#!/usr/bin/env python3
"""Export training-visible rows from stored banger question artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from discovery.question_context import training_rows_from_final_questions


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FINAL_QA = (
    REPO_ROOT / "discovery_codex_15m" / "04_b_to_q" / "final_qa.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Flatten stored question artifacts into training-visible JSONL rows "
            "containing only context_events, question, and answer."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_FINAL_QA,
        help=(
            "Path to final_qa.json, a question_*.json file, or a "
            "04_b_to_q directory. Defaults to discovery_codex_15m/04_b_to_q/"
            "final_qa.json."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSONL path. Defaults to stdout.",
    )
    return parser.parse_args()


def load_question_items(path: Path) -> list[dict[str, Any]]:
    if path.is_dir():
        final_qa_path = path / "final_qa.json"
        if final_qa_path.exists():
            return load_question_items(final_qa_path)
        generic_qa_paths = sorted(path.glob("*/qa_*.json"))
        if generic_qa_paths:
            return [
                {"qa": load_json(qa_path)}
                for qa_path in generic_qa_paths
            ]
        return [
            {"questions": load_json(question_path)}
            for question_path in sorted(path.glob("question_*.json"))
        ]

    data = load_json(path)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return [{"questions": data}]
    raise SystemExit(f"expected JSON object or array in {path}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"input not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from exc


def write_rows(rows: list[dict[str, Any]], output: Path | None) -> None:
    lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
    text = "\n".join(lines)
    if text:
        text += "\n"

    if output is None:
        sys.stdout.write(text)
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = training_rows_from_final_questions(load_question_items(args.input))
    write_rows(rows, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
