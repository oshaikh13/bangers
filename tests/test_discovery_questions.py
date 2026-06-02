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
from discovery.cli import parse_args
from discovery.runner import (
    load_suggestions_from_bangers,
    sample_question_suggestions,
    validate_questions_data,
    write_final_questions,
)


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
        data["threads"][0]["qa_pairs"][0]["question_basis"]["context_event_indexes"] = [3]

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

    def test_question_sampling_defaults_to_ten_percent_deterministically(self) -> None:
        suggestions = [{"_question_id": str(index)} for index in range(20)]

        selected = sample_question_suggestions(suggestions, 0.10, "seed")
        selected_again = sample_question_suggestions(suggestions, 0.10, "seed")

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected, selected_again)
        self.assertNotEqual(selected, suggestions[:2])

    def test_question_sampling_can_select_all(self) -> None:
        suggestions = [{"_question_id": str(index)} for index in range(20)]

        self.assertEqual(
            sample_question_suggestions(suggestions, 1.0, "seed"),
            suggestions,
        )

    def test_load_suggestions_samples_before_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bangers_dir = Path(tmp_dir) / "03_bangers"
            bangers_dir.mkdir()
            _write_bangers_batch(bangers_dir / "bangers_0_19.json", range(20))

            args = parse_args(
                [
                    "--questions",
                    "--bangers-dir",
                    str(bangers_dir),
                    "--questions-sample-fraction",
                    "0.5",
                    "--questions-sample-seed",
                    "seed",
                    "--limit",
                    "3",
                ]
            )

            selected = load_suggestions_from_bangers(args)
            sampled_without_limit = load_suggestions_from_bangers(
                parse_args(
                    [
                        "--questions",
                        "--bangers-dir",
                        str(bangers_dir),
                        "--questions-sample-fraction",
                        "0.5",
                        "--questions-sample-seed",
                        "seed",
                    ]
                )
            )

            self.assertEqual(len(selected), 3)
            self.assertEqual(len(sampled_without_limit), 10)
            self.assertEqual(selected, sampled_without_limit[:3])

    def test_parse_rejects_invalid_question_sample_fraction(self) -> None:
        with self.assertRaisesRegex(SystemExit, "questions-sample-fraction"):
            parse_args(["--questions", "--questions-sample-fraction", "0"])

    def test_training_export_omits_metadata(self) -> None:
        rows = training_rows_from_final_questions(
            [
                {
                    "questions": _valid_questions_payload(),
                    "suggestion": {"suggestion": "hidden"},
                }
            ]
        )

        self.assertEqual(len(rows), 9)
        self.assertEqual(
            set(rows[0].keys()),
            {"context_events", "thread_id", "q_id", "question", "answer"},
        )
        self.assertNotIn("why_it_matters", rows[0])
        self.assertEqual(
            set(rows[0]["context_events"][0].keys()),
            {"index", "ts", "ts_iso", "connector", "text"},
        )
        self.assertEqual(rows[0]["thread_id"], 0)
        self.assertEqual(rows[0]["q_id"], 0)
        self.assertEqual(rows[-1]["thread_id"], 2)
        self.assertEqual(rows[-1]["q_id"], 2)


def _valid_questions_payload() -> dict:
    def _pair(q_id: int) -> dict:
        return {
            "q_id": q_id,
            "question": f"What is the user trying to get done right now? ({q_id})",
            "answer": "The user is trying to make a checklist.",
            "question_basis": {
                "context_event_indexes": [0],
                "reason": "The event shows the current workflow.",
            },
            "why_it_matters": "It keeps the banger focused.",
            "evidence_grounding": "No future evidence was needed for this answer.",
            "question_difficulty": 2,
        }

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
        "threads": [
            {"thread_id": thread_id, "qa_pairs": [_pair(0), _pair(1), _pair(2)]}
            for thread_id in range(3)
        ],
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_bangers_batch(path: Path, indexes: range) -> None:
    data = {
        "bangers": [
            {
                "input_index": index,
                "goals": [
                    {
                        "goal": f"Goal {index}",
                        "opportunities": [
                            {
                                "timestamp": float(index),
                                "suggestion": f"Suggestion {index}",
                            }
                        ],
                    }
                ],
            }
            for index in indexes
        ]
    }
    path.write_text(json.dumps(data), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
