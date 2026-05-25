from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from discovery.prompts import render_questions_prompt
from discovery.question_context import (
    context_events_for_timestamp,
    load_indexed_events,
    training_rows_from_final_questions,
)
from discovery.runner import validate_questions_data, write_final_questions


class QuestionContextTests(unittest.TestCase):
    def test_loads_events_sorted_across_connectors_and_selects_latest_100(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            logs_dir = Path(tmp_dir) / "logs-indexed"
            screen_dir = logs_dir / "screen"
            calendar_dir = logs_dir / "calendar"
            screen_dir.mkdir(parents=True)
            calendar_dir.mkdir(parents=True)

            screen_rows = [
                {
                    "ts": float(index),
                    "ts_iso": f"2026-01-01T00:{index:02d}:00Z",
                    "connector": "screen",
                    "text": f"screen {index}",
                }
                for index in range(0, 150, 2)
            ]
            calendar_rows = [
                {
                    "ts": float(index),
                    "ts_iso": f"2026-01-01T00:{index:02d}:00Z",
                    "connector": "calendar",
                    "text": f"calendar {index}",
                }
                for index in range(1, 150, 2)
            ]
            _write_jsonl(screen_dir / "2026-01-01.jsonl", screen_rows)
            _write_jsonl(calendar_dir / "2026-01-01.jsonl", calendar_rows)

            events = load_indexed_events(logs_dir)
            self.assertEqual([event["ts"] for event in events[:4]], [0.0, 1.0, 2.0, 3.0])

            context = context_events_for_timestamp(events, 149.0)
            self.assertEqual(len(context), 100)
            self.assertEqual(context[0]["ts"], 50.0)
            self.assertEqual(context[-1]["ts"], 149.0)
            self.assertEqual([event["index"] for event in context], list(range(100)))

    def test_render_questions_prompt_includes_context_events(self) -> None:
        prompt = render_questions_prompt(
            "suggestion={suggestion_json}\ncontext={context_events_json}",
            {"timestamp": "2026-01-01T00:00:00Z", "suggestion": "Make a checklist"},
            [{"index": 0, "ts": 1.0, "ts_iso": "x", "connector": "screen", "text": "event"}],
            Path("/tmp/question.json"),
            "codex",
        )

        self.assertIn('"suggestion": "Make a checklist"', prompt)
        self.assertIn('"text": "event"', prompt)
        self.assertIn("/tmp/question.json", prompt)

    def test_validate_questions_rejects_missing_context_basis(self) -> None:
        data = _valid_questions_payload()
        data["qa_pairs"][0]["question_basis"]["context_event_indexes"] = [3]

        with self.assertRaisesRegex(RuntimeError, "references missing context event index"):
            validate_questions_data(data, "question.json")

    def test_write_final_questions_preserves_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            questions_dir = Path(tmp_dir) / "04_questions"
            questions_dir.mkdir()
            path = questions_dir / "question_0_0_0.json"
            data = _valid_questions_payload()
            data.pop("context_events")
            path.write_text(json.dumps(data), encoding="utf-8")

            args = SimpleNamespace(questions_dir=questions_dir)
            suggestion = {
                "_question_id": "0_0_0",
                "_combined_index": 0,
                "_goal_index": 0,
                "_opportunity_index": 0,
                "timestamp": 1.0,
                "suggestion": "Make a checklist",
            }
            indexed_events = [
                {
                    "ts": 1.0,
                    "ts_iso": "2026-01-01T00:00:01Z",
                    "connector": "screen",
                    "text": "event",
                }
            ]

            write_final_questions(args, [suggestion], indexed_events)

            final_data = json.loads((questions_dir / "final_questions.json").read_text())
            self.assertEqual(final_data[0]["context_events"][0]["text"], "event")
            self.assertEqual(final_data[0]["questions"]["context_events"][0]["text"], "event")

    def test_training_export_omits_metadata(self) -> None:
        rows = training_rows_from_final_questions(
            [
                {
                    "questions": _valid_questions_payload(),
                    "suggestion": {"suggestion": "hidden"},
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0].keys()), {"context_events", "question", "answer"})
        self.assertNotIn("why_it_matters", rows[0])
        self.assertEqual(
            set(rows[0]["context_events"][0].keys()),
            {"index", "ts", "ts_iso", "connector", "text"},
        )


def _valid_questions_payload() -> dict:
    return {
        "suggestion_title": "Make a checklist",
        "banger_timestamp": "2026-01-01T00:00:01Z",
        "context_events": [
            {
                "index": 0,
                "ts": 1.0,
                "ts_iso": "2026-01-01T00:00:01Z",
                "connector": "screen",
                "text": "event",
            }
        ],
        "qa_pairs": [
            {
                "question": "What is the user trying to get done right now?",
                "answer": "The user is trying to make a checklist.",
                "banger_dimension": "goal_clarity",
                "question_basis": {
                    "context_event_indexes": [0],
                    "reason": "The event shows the current workflow.",
                },
                "why_it_matters": "It keeps the banger focused.",
                "evidence_grounding": "No future evidence was needed for this answer.",
                "question_difficulty": 2,
            }
        ],
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
