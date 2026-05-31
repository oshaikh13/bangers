from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from discovery.pre_banger_qa import (
    final_pre_banger_qa_path,
    load_pre_banger_qa_template,
    load_seed_filter,
    load_seed_filter_template,
    parse_qa_types,
    select_filtered_seeds,
    select_seed_candidates_for_ranking,
    validate_seed_filter_data,
    validate_pre_banger_qa_data,
    write_final_pre_banger_qa,
)
from discovery.prompts import (
    render_pre_banger_qa_prompt,
    render_pre_banger_seed_filter_prompt,
)
from discovery.question_context import training_rows_from_final_questions


class PreBangerQATests(unittest.TestCase):
    def test_parse_qa_types_expands_all_and_dedupes(self) -> None:
        self.assertIn("threaded_mix", parse_qa_types("all"))
        self.assertEqual(
            parse_qa_types("curiosity,engagement,curiosity"),
            ["curiosity", "engagement"],
        )

    def test_seed_ranking_prompt_and_loader_preserve_scored_order(self) -> None:
        all_seeds = [
            {"seed_id": "self_done", "banger_timestamp": 0.0},
            {"seed_id": "cool_open", "banger_timestamp": 0.0},
        ]
        args = SimpleNamespace(
            seed_filter_template=REPO_ROOT / "prompts" / "20_pre_banger_filter.md"
        )
        template = load_seed_filter_template(args)
        prompt = render_pre_banger_seed_filter_prompt(
            template,
            all_seeds,
            Path("/tmp/seed_rankings.json"),
            "codex",
        )

        self.assertIn("Do not merely sort by the original numeric fields", prompt)
        self.assertIn("intervention_value_now", prompt)
        self.assertIn('"seed_id": "cool_open"', prompt)

        with tempfile.TemporaryDirectory() as tmp_dir:
            filter_path = Path(tmp_dir) / "seed_rankings.json"
            filter_path.write_text(
                json.dumps(
                    {
                        "seeds": [
                            {
                                "rank": 1,
                                "seed_id": "cool_open",
                                "user_value": 9,
                                "intervention_value_now": 8,
                                "intervention_posture": "surface_now",
                                "negative_reason": "none",
                                "engagement_pull": 8,
                                "surprise": 8,
                                "personal_relevance": 9,
                                "disregard": 8,
                                "grounding": 9,
                                "self_done_penalty": 2,
                                "timing_reason": "The user is circling scattered context.",
                                "marginal_value_reason": "The assistant can synthesize before the loop continues.",
                                "self_done_reason": "The user is unlikely to assemble it immediately.",
                                "future_check": "The topic was touched but not resolved.",
                            },
                            {
                                "rank": 2,
                                "seed_id": "self_done",
                                "user_value": 7,
                                "intervention_value_now": 2,
                                "intervention_posture": "stay_quiet",
                                "negative_reason": "self_done",
                                "engagement_pull": 4,
                                "surprise": 2,
                                "personal_relevance": 7,
                                "disregard": 1,
                                "grounding": 8,
                                "self_done_penalty": 9,
                                "timing_reason": "The user is already doing the work.",
                                "marginal_value_reason": "The assistant adds little right now.",
                                "self_done_reason": "The user drives the same work immediately.",
                                "future_check": "The user drove the same work.",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            validate_seed_filter_data(json.loads(filter_path.read_text()), all_seeds, filter_path)
            selected = load_seed_filter(filter_path, all_seeds)

        self.assertEqual([seed["seed_id"] for seed in selected], ["cool_open", "self_done"])
        self.assertEqual(selected[0]["ranking_metadata"]["intervention_value_now"], 8)
        self.assertEqual(selected[1]["ranking_metadata"]["intervention_posture"], "stay_quiet")
        self.assertEqual(selected[1]["ranking_metadata"]["negative_reason"], "self_done")

    def test_seed_ranking_rejects_binary_selection_label(self) -> None:
        all_seeds = [{"seed_id": "old_shape", "banger_timestamp": 0.0}]
        data = {
            "seeds": [
                {
                    "rank": 1,
                    "seed_id": "old_shape",
                    "selection_label": "keep",
                }
            ]
        }

        with self.assertRaisesRegex(RuntimeError, "must not include selection_label"):
            validate_seed_filter_data(data, all_seeds, "seed_rankings.json")

    def test_interval_rows_select_seed_candidates_by_banger_timestamp(self) -> None:
        seeds = [
            {
                "seed_id": "inside",
                "combined_index": 25,
                "banger_timestamp": "2026-04-08T16:31:46.325Z",
            },
            {
                "seed_id": "outside",
                "combined_index": 29,
                "banger_timestamp": "2026-04-08T18:00:00Z",
            },
        ]
        interval_rows = [
            {
                "interval_index": 45,
                "start_ts": 1775665424.439826,
                "end_ts": 1775666324.439826,
            }
        ]
        args = SimpleNamespace(seed_ids=None, combined_indexes=None, start=0, limit=None)

        selected = select_seed_candidates_for_ranking(args, seeds, interval_rows)

        self.assertEqual([seed["seed_id"] for seed in selected], ["inside"])

    def test_select_filtered_seeds_combines_interval_and_start_limit(self) -> None:
        seeds = [
            {
                "seed_id": "first",
                "combined_index": 25,
                "banger_timestamp": "2026-04-08T16:31:46.325Z",
            },
            {
                "seed_id": "second",
                "combined_index": 26,
                "banger_timestamp": "2026-04-08T16:32:00Z",
            },
            {
                "seed_id": "outside",
                "combined_index": 29,
                "banger_timestamp": "2026-04-08T18:00:00Z",
            },
        ]
        interval_rows = [
            {
                "interval_index": 45,
                "start_ts": 1775665424.439826,
                "end_ts": 1775666324.439826,
            }
        ]
        args = SimpleNamespace(
            seed_ids=None,
            combined_indexes=None,
            start=1,
            limit=1,
        )

        selected = select_filtered_seeds(args, seeds, interval_rows)

        self.assertEqual([seed["seed_id"] for seed in selected], ["second"])

    def test_load_and_render_prompt_includes_hidden_seed_and_context(self) -> None:
        args = SimpleNamespace(
            common_template=REPO_ROOT / "prompts" / "20_pre_banger_common.md",
            prompts_dir=REPO_ROOT / "prompts",
        )
        template = load_pre_banger_qa_template(args, "curiosity")
        context = [_context_event()]
        seed = _seed()

        prompt = render_pre_banger_qa_prompt(
            template,
            "curiosity",
            seed,
            context,
            Path("/tmp/qa_29_0_0.json"),
            "codex",
            6,
        )

        self.assertIn("QA Type: Pre-Banger Curiosity", prompt)
        self.assertIn('"seed_id": "29_0_0"', prompt)
        self.assertIn('"text": "Visible context"', prompt)
        self.assertIn("surface help now, wait, or stay quiet", prompt)
        self.assertIn("/tmp/qa_29_0_0.json", prompt)

    def test_validate_pre_banger_accepts_flat_payload(self) -> None:
        validate_pre_banger_qa_data(_valid_flat_payload(), "qa.json")

    def test_validate_pre_banger_accepts_threaded_payload(self) -> None:
        validate_pre_banger_qa_data(_valid_threaded_payload(), "qa.json")

    def test_validate_pre_banger_rejects_missing_context_basis(self) -> None:
        data = _valid_flat_payload()
        data["qa_pairs"][0]["question_basis"]["context_event_indexes"] = [2]

        with self.assertRaisesRegex(RuntimeError, "references missing context event index"):
            validate_pre_banger_qa_data(data, "qa.json")

    def test_write_final_pre_banger_qa_consolidates_flat_and_threaded_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pre_banger_dir = Path(tmp_dir) / "20_pre_banger_qa"
            flat_dir = pre_banger_dir / "curiosity"
            threaded_dir = pre_banger_dir / "threaded_mix"
            flat_dir.mkdir(parents=True)
            threaded_dir.mkdir(parents=True)
            (flat_dir / "qa_29_0_0.json").write_text(
                json.dumps(_valid_flat_payload()),
                encoding="utf-8",
            )
            (threaded_dir / "qa_29_0_0.json").write_text(
                json.dumps(_valid_threaded_payload()),
                encoding="utf-8",
            )

            write_final_pre_banger_qa(
                SimpleNamespace(pre_banger_qa_dir=pre_banger_dir, interval_indexes=None)
            )

            final_data = json.loads((pre_banger_dir / "final_qa.json").read_text())
            self.assertEqual(len(final_data), 2)
            self.assertEqual({item["qa_type"] for item in final_data}, {"curiosity", "threaded_mix"})

    def test_write_final_pre_banger_qa_uses_interval_specific_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pre_banger_dir = Path(tmp_dir) / "20_pre_banger_qa"
            flat_dir = pre_banger_dir / "timing"
            flat_dir.mkdir(parents=True)
            (flat_dir / "qa_29_0_0.json").write_text(
                json.dumps(_valid_flat_payload("timing")),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                pre_banger_qa_dir=pre_banger_dir,
                interval_indexes="40-49",
            )

            write_final_pre_banger_qa(args)

            final_path = pre_banger_dir / "final_qa_intervals_40-49.json"
            self.assertEqual(final_pre_banger_qa_path(args), final_path)
            self.assertTrue(final_path.exists())
            self.assertFalse((pre_banger_dir / "final_qa.json").exists())

    def test_training_export_flattens_shapes_and_drops_seed_metadata(self) -> None:
        rows = training_rows_from_final_questions(
            [
                {"qa": _valid_flat_payload(), "qa_type": "curiosity"},
                {"qa": _valid_threaded_payload(), "qa_type": "threaded_mix"},
            ]
        )

        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["qa_type"], "curiosity")
        self.assertEqual(rows[0]["category"], "pre_banger_curiosity")
        self.assertNotIn("target_banger", rows[0])
        self.assertNotIn("seed_id", rows[0])
        self.assertEqual(rows[-1]["thread_id"], 2)

    def test_threaded_questions_are_intervention_oriented(self) -> None:
        prompt_text = (REPO_ROOT / "prompts" / "20_pre_banger_threaded_mix.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("likely next action -> intervention value", prompt_text)
        self.assertIn("stay quiet", prompt_text)
        self.assertIn("Avoid questions that over-specify document structure", prompt_text)


def _context_event() -> dict:
    return {
        "index": 0,
        "ts": 99.0,
        "ts_iso": "2026-01-01T00:01:39Z",
        "connector": "screen",
        "text": "Visible context",
    }


def _seed() -> dict:
    return {
        "seed_id": "29_0_0",
        "banger_timestamp": 100.0,
        "goal": "Have protected research time",
        "suggestion": "I can surface a stabilization charter.",
        "expected_artifact": "stabilization_charter_and_research_protection_plan",
        "ranking_metadata": {
            "user_value": 9,
            "intervention_value_now": 8,
            "intervention_posture": "surface_now",
            "negative_reason": "none",
            "timing_reason": "The user is at a high-leverage intervention moment.",
        },
    }


def _pair(
    q_id: int,
    question: str,
    category: str,
    answer_basis: str = "H+F",
    verify_at_ts: float = 101.0,
) -> dict:
    return {
        "q_id": q_id,
        "question": question,
        "answer": "The assistant should surface help now because it would add timely marginal value.",
        "category": category,
        "timescale": "micro",
        "answer_basis": answer_basis,
        "verify_at_ts": verify_at_ts,
        "verify_at_iso": "2026-01-01T00:01:41Z",
        "question_basis": {
            "context_event_indexes": [0],
            "reason": "The visible event makes this natural to ask.",
        },
        "why_it_matters": "It helps decide whether proactive help is useful now.",
        "evidence_grounding": "The answer is grounded in test events.",
        "question_difficulty": 2,
    }


def _valid_flat_payload(qa_type: str = "curiosity") -> dict:
    category = f"pre_banger_{qa_type}"
    return {
        "qa_type": qa_type,
        "seed_id": "29_0_0",
        "banger_timestamp": 100.0,
        "target_banger": {"suggestion": "hidden"},
        "context_events": [_context_event()],
        "qa_pairs": [
            _pair(0, "What would the user be curious to see right now?", category),
            _pair(1, "Is now a good moment for the assistant to help?", category),
            _pair(2, "What would the user likely do without help?", category),
        ],
    }


def _valid_threaded_payload() -> dict:
    def thread(thread_id: int) -> dict:
        return {
            "thread_id": thread_id,
            "qa_pairs": [
                _pair(0, "What is the user circling around?", "pre_banger_threaded_mix"),
                _pair(1, "What would the user likely do next?", "pre_banger_threaded_mix"),
                _pair(2, "Should the assistant surface help now?", "pre_banger_threaded_mix"),
            ],
        }

    return {
        "qa_type": "threaded_mix",
        "seed_id": "29_0_0",
        "banger_timestamp": 100.0,
        "target_banger": {"suggestion": "hidden"},
        "context_events": [_context_event()],
        "threads": [thread(0), thread(1), thread(2)],
    }


if __name__ == "__main__":
    unittest.main()
