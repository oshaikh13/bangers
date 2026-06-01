from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from discovery.generic_qa import (
    context_for_interval,
    load_generic_qa_template,
    parse_qa_types,
    validate_generic_qa_data,
    write_final_generic_qa,
)
from discovery.prompts import render_generic_qa_prompt
from discovery.question_context import training_rows_from_final_questions


class GenericQATests(unittest.TestCase):
    def test_parse_qa_types_expands_all_and_dedupes_specific_types(self) -> None:
        self.assertIn("activity_window", parse_qa_types("all"))
        self.assertIn("verbatim_textbox", parse_qa_types("all"))
        self.assertEqual(
            parse_qa_types("recall,verbatim_textbox,recall"),
            ["recall", "verbatim_textbox"],
        )

    def test_context_for_interval_uses_latest_100_events_before_end_ts(self) -> None:
        events = [
            {
                "ts": float(index),
                "ts_iso": f"2026-01-01T00:{index:02d}:00Z",
                "connector": "screen",
                "text": f"event {index}",
            }
            for index in range(120)
        ]
        row = {"interval_index": 7, "end_ts": 119.0, "end_utc": "2026-01-01T02:00:00Z"}

        context = context_for_interval(events, row)

        self.assertEqual(len(context), 100)
        self.assertEqual(context[0]["ts"], 20.0)
        self.assertEqual(context[-1]["ts"], 119.0)
        self.assertEqual([event["index"] for event in context], list(range(100)))

    def test_load_and_render_prompt_includes_type_interval_and_context(self) -> None:
        args = SimpleNamespace(
            common_template=REPO_ROOT / "prompts" / "10_generic_qa_common.md",
            prompts_dir=REPO_ROOT / "prompts",
        )
        template = load_generic_qa_template(args, "activity_window")
        row = {"interval_index": 0, "end_ts": 1.0, "end_utc": "2026-01-01T00:00:01Z"}
        context = [
            {
                "index": 0,
                "ts": 1.0,
                "ts_iso": "2026-01-01T00:00:01Z",
                "connector": "screen",
                "text": "Visible event",
            }
        ]

        prompt = render_generic_qa_prompt(
            template,
            "activity_window",
            row,
            context,
            Path("/tmp/qa.json"),
            "codex",
            10,
        )

        self.assertIn("QA Type: Activity Window", prompt)
        self.assertIn('"text": "Visible event"', prompt)
        self.assertIn('"interval_index": 0', prompt)
        self.assertIn("/tmp/qa.json", prompt)

    def test_load_and_render_verbatim_textbox_prompt(self) -> None:
        args = SimpleNamespace(
            common_template=REPO_ROOT / "prompts" / "10_generic_qa_common.md",
            prompts_dir=REPO_ROOT / "prompts",
        )
        template = load_generic_qa_template(args, "verbatim_textbox")
        row = {"interval_index": 0, "end_ts": 1.0, "end_utc": "2026-01-01T00:00:01Z"}

        prompt = render_generic_qa_prompt(
            template,
            "verbatim_textbox",
            row,
            [],
            Path("/tmp/qa.json"),
            "codex",
            10,
        )

        self.assertIn("QA Type: Verbatim Textbox", prompt)
        self.assertIn("preserving spelling, casing, punctuation", prompt)
        self.assertIn('output `"qa_pairs": []`', prompt)

    def test_validate_generic_qa_accepts_flat_payload_with_mixed_grounding(self) -> None:
        validate_generic_qa_data(_valid_generic_qa_payload(), "qa.json")

    def test_validate_generic_qa_allows_empty_sparse_verbatim_textbox_payload(self) -> None:
        data = {
            **_valid_generic_qa_payload(),
            "qa_type": "verbatim_textbox",
            "qa_pairs": [],
        }

        validate_generic_qa_data(data, "qa.json")

    def test_validate_generic_qa_accepts_legacy_threaded_payload(self) -> None:
        flat = _valid_generic_qa_payload()
        legacy = {**flat, "threads": [{"thread_id": 0, "qa_pairs": flat["qa_pairs"]}]}
        legacy.pop("qa_pairs")
        validate_generic_qa_data(legacy, "qa.json")

    def test_validate_generic_qa_rejects_missing_context_basis(self) -> None:
        data = _valid_generic_qa_payload()
        data["qa_pairs"][0]["question_basis"]["context_event_indexes"] = [2]

        with self.assertRaisesRegex(RuntimeError, "references missing context event index"):
            validate_generic_qa_data(data, "qa.json")

    def test_validate_generic_qa_rejects_bad_timestamp_grounding(self) -> None:
        data = _valid_generic_qa_payload()
        data["qa_pairs"][0]["answer_basis"] = "H"
        data["qa_pairs"][0]["verify_at_ts"] = 100.0

        with self.assertRaisesRegex(RuntimeError, "before qa_timestamp"):
            validate_generic_qa_data(data, "qa.json")

        data = _valid_generic_qa_payload()
        data["qa_pairs"][1]["answer_basis"] = "F"
        data["qa_pairs"][1]["verify_at_ts"] = 99.0

        with self.assertRaisesRegex(RuntimeError, "at or after qa_timestamp"):
            validate_generic_qa_data(data, "qa.json")

    def test_write_final_generic_qa_consolidates_completed_type_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            generic_qa_dir = Path(tmp_dir) / "10_generic_qa"
            type_dir = generic_qa_dir / "activity_window"
            type_dir.mkdir(parents=True)
            (type_dir / "qa_0.json").write_text(
                json.dumps(_valid_generic_qa_payload()),
                encoding="utf-8",
            )

            write_final_generic_qa(SimpleNamespace(generic_qa_dir=generic_qa_dir))

            final_data = json.loads((generic_qa_dir / "final_qa.json").read_text())
            self.assertEqual(len(final_data), 1)
            self.assertEqual(final_data[0]["qa_type"], "activity_window")
            self.assertEqual(final_data[0]["interval_index"], 0)
            self.assertEqual(len(final_data[0]["qa"]["qa_pairs"]), 3)
            self.assertNotIn("threads", final_data[0]["qa"])

    def test_training_export_includes_generic_qa_metadata(self) -> None:
        rows = training_rows_from_final_questions(
            [{"qa": _valid_generic_qa_payload(), "qa_type": "activity_window"}]
        )

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["qa_type"], "activity_window")
        self.assertEqual(rows[0]["category"], "activity_window")
        self.assertEqual(rows[0]["question"], "What did the user just finish?")


def _valid_generic_qa_payload() -> dict:
    def _pair(
        q_id: int,
        question: str,
        answer_basis: str,
        verify_at_ts: float,
    ) -> dict:
        return {
            "q_id": q_id,
            "question": question,
            "answer": "The user is working from the visible context.",
            "category": "activity_window",
            "timescale": "micro",
            "answer_basis": answer_basis,
            "verify_at_ts": verify_at_ts,
            "verify_at_iso": "2026-01-01T00:01:40Z",
            "question_basis": {
                "context_event_indexes": [0],
                "reason": "The visible event makes the question askable.",
            },
            "why_it_matters": "It trains useful user prediction.",
            "evidence_grounding": "The answer is grounded in test events.",
            "question_difficulty": 1,
        }

    return {
        "qa_type": "activity_window",
        "qa_timestamp": "2026-01-01T00:01:40Z",
        "qa_timestamp_ts": 100.0,
        "interval": {
            "interval_index": 0,
            "end_ts": 100.0,
            "end_utc": "2026-01-01T00:01:40Z",
        },
        "context_events": [
            {
                "index": 0,
                "ts": 99.0,
                "ts_iso": "2026-01-01T00:01:39Z",
                "connector": "screen",
                "text": "event",
            }
        ],
        "qa_pairs": [
            _pair(0, "What did the user just finish?", "H", 99.0),
            _pair(1, "What will the user do next?", "F", 100.0),
            _pair(2, "What will this turn into?", "H+F", 101.0),
        ],
    }


if __name__ == "__main__":
    unittest.main()
