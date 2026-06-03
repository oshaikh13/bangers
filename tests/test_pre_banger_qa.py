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
    enrich_seed_filter_file,
    final_pre_banger_qa_path,
    load_pre_banger_qa_template,
    load_seed_filter,
    load_seed_filter_template,
    parse_args,
    parse_qa_types,
    ranked_seed_metadata,
    sample_pre_banger_seeds,
    select_filtered_seeds,
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
        self.assertEqual(
            parse_qa_types("all"),
            ["timing", "curiosity", "disregard", "value", "threaded"],
        )
        self.assertEqual(
            parse_qa_types("curiosity,threaded,curiosity"),
            ["curiosity", "threaded"],
        )

    def test_default_pair_budgets_are_reduced(self) -> None:
        args = parse_args(["--interval-range", "0-0", "--run-root", "/tmp/run"])

        self.assertEqual(args.pairs_per_run, 3)
        self.assertEqual(args.threaded_pairs_per_run, 10)

    def test_rank_only_force_regenerates_seed_ranking(self) -> None:
        args = parse_args(
            [
                "--interval-range",
                "0-0",
                "--run-root",
                "/tmp/run",
                "--rank-only",
                "--force",
            ]
        )

        self.assertTrue(args.force_seed_filter)

    def test_interval_runs_use_interval_scoped_paths(self) -> None:
        args = parse_args(["--interval-range", "40-49", "--run-root", "/tmp/run"])

        self.assertEqual(args.scope_slug, "intervals_40-49")
        self.assertEqual(args.bangers_dir, Path("/tmp/run/03_bangers").resolve())
        self.assertEqual(args.pre_banger_qa_dir, Path("/tmp/run/05_q_to_b").resolve())
        self.assertEqual(
            args.seed_filter_path,
            Path("/tmp/run/03_bangers/seed_rankings.json").resolve(),
        )
        self.assertEqual(args.combined_bangers_path.name, "combined_bangers.json")
        self.assertEqual(final_pre_banger_qa_path(args).name, "final_qa.json")

    def test_seed_ranking_prompt_and_loader_preserve_scored_order(self) -> None:
        all_seeds = [
            {
                "seed_id": "self_done",
                "banger_timestamp": 0.0,
                "suggestion": "I can prepare the obvious next step.",
            },
            {
                "seed_id": "cool_open",
                "banger_timestamp": 0.0,
                "target_banger": {
                    "suggestion": "I can synthesize the scattered context.",
                },
            },
        ]
        args = SimpleNamespace(
            seed_filter_template=REPO_ROOT / "prompts" / "03_bangers" / "rank_bangers.md"
        )
        template = load_seed_filter_template(args)
        prompt = render_pre_banger_seed_filter_prompt(
            template,
            Path("/tmp/combined_bangers.json"),
            Path("/tmp/seed_rankings.json"),
            "codex",
        )

        self.assertIn("Do not merely sort by the original numeric fields", prompt)
        self.assertIn("intervention_value_now", prompt)
        self.assertIn("/tmp/combined_bangers.json", prompt)
        self.assertIn("top-level `seeds` array", prompt)
        self.assertIn("one interval-range run", prompt)
        self.assertIn("stage `03_bangers`", prompt)
        self.assertIn("Include every candidate seed exactly once", prompt)

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
            enrich_seed_filter_file(filter_path, all_seeds)
            selected = load_seed_filter(filter_path, all_seeds)
            persisted = json.loads(filter_path.read_text(encoding="utf-8"))

        self.assertEqual([seed["seed_id"] for seed in selected], ["cool_open", "self_done"])
        self.assertEqual(
            selected[0]["ranking_metadata"]["suggestion"],
            "I can synthesize the scattered context.",
        )
        self.assertEqual(
            selected[1]["ranking_metadata"]["suggestion"],
            "I can prepare the obvious next step.",
        )
        self.assertEqual(selected[0]["ranking_metadata"]["intervention_value_now"], 8)
        self.assertEqual(selected[0]["ranking_metadata"]["rank_count"], 2)
        self.assertEqual(selected[0]["ranking_metadata"]["rank_percentile"], 100.0)
        self.assertEqual(selected[0]["ranking_metadata"]["value_estimate"], 100)
        self.assertEqual(selected[1]["ranking_metadata"]["intervention_posture"], "stay_quiet")
        self.assertEqual(selected[1]["ranking_metadata"]["negative_reason"], "self_done")
        self.assertEqual(selected[1]["ranking_metadata"]["rank_percentile"], 0.0)
        self.assertEqual(selected[1]["ranking_metadata"]["value_estimate"], 1)

        self.assertEqual(
            [seed["suggestion"] for seed in persisted["seeds"]],
            [
                "I can synthesize the scattered context.",
                "I can prepare the obvious next step.",
            ],
        )

    def test_ranked_seed_metadata_derives_continuous_value_estimate(self) -> None:
        self.assertEqual(
            ranked_seed_metadata({"rank": 1, "seed_id": "only"}, 1)["value_estimate"],
            100,
        )
        self.assertEqual(
            ranked_seed_metadata({"rank": 1, "seed_id": "first"}, 5)["value_estimate"],
            100,
        )

        middle = ranked_seed_metadata({"rank": 3, "seed_id": "middle"}, 5)
        self.assertEqual(middle["rank_percentile"], 50.0)
        self.assertEqual(middle["value_estimate"], 50)

        last = ranked_seed_metadata({"rank": 5, "seed_id": "last"}, 5)
        self.assertEqual(last["rank_percentile"], 0.0)
        self.assertEqual(last["value_estimate"], 1)

    def test_select_filtered_seeds_applies_start_limit(self) -> None:
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
        args = SimpleNamespace(
            seed_ids=None,
            banger_input_indexes=None,
            start=1,
            limit=1,
            seed_sample_fraction=1.0,
            seed_sample_seed="seed",
        )

        selected = select_filtered_seeds(args, seeds)

        self.assertEqual([seed["seed_id"] for seed in selected], ["second"])

    def test_pre_banger_seed_sampling_defaults_to_ten_percent_deterministically(self) -> None:
        seeds = [{"seed_id": str(index)} for index in range(20)]

        selected = sample_pre_banger_seeds(seeds, 0.10, "seed")
        selected_again = sample_pre_banger_seeds(seeds, 0.10, "seed")

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected, selected_again)
        self.assertNotEqual(selected, seeds[:2])

    def test_pre_banger_seed_sampling_is_stratified_by_rank(self) -> None:
        seeds = [{"seed_id": str(index)} for index in range(100)]

        selected = sample_pre_banger_seeds(seeds, 0.10, "seed")
        selected_indexes = [int(item["seed_id"]) for item in selected]

        self.assertEqual(len(selected_indexes), 10)
        for bucket_index, selected_index in enumerate(selected_indexes):
            self.assertGreaterEqual(selected_index, bucket_index * 10)
            self.assertLess(selected_index, (bucket_index + 1) * 10)

    def test_pre_banger_seed_sampling_can_select_all(self) -> None:
        seeds = [{"seed_id": str(index)} for index in range(20)]

        self.assertEqual(sample_pre_banger_seeds(seeds, 1.0, "seed"), seeds)

    def test_select_filtered_seeds_samples_before_limit(self) -> None:
        seeds = [
            {
                "seed_id": str(index),
                "combined_index": index,
                "banger_timestamp": "2026-04-08T16:31:46.325Z",
            }
            for index in range(20)
        ]
        args = SimpleNamespace(
            seed_ids=None,
            banger_input_indexes=None,
            start=0,
            limit=3,
            seed_sample_fraction=0.5,
            seed_sample_seed="seed",
        )
        args_without_limit = SimpleNamespace(
            seed_ids=None,
            banger_input_indexes=None,
            start=0,
            limit=None,
            seed_sample_fraction=0.5,
            seed_sample_seed="seed",
        )

        selected = select_filtered_seeds(args, seeds)
        sampled_without_limit = select_filtered_seeds(args_without_limit, seeds)

        self.assertEqual(len(selected), 3)
        self.assertEqual(len(sampled_without_limit), 10)
        self.assertEqual(selected, sampled_without_limit[:3])

    def test_parse_rejects_invalid_seed_sample_fraction(self) -> None:
        with self.assertRaisesRegex(SystemExit, "seed-sample-fraction"):
            parse_args(
                [
                    "--interval-range",
                    "0-0",
                    "--run-root",
                    "/tmp/run",
                    "--seed-sample-fraction",
                    "0",
                ]
            )

    def test_load_and_render_prompt_includes_hidden_seed_and_context(self) -> None:
        args = SimpleNamespace(
            common_template=REPO_ROOT / "prompts" / "05_q_to_b" / "common.md",
            prompts_dir=REPO_ROOT / "prompts" / "05_q_to_b",
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
        self.assertIn("attention, preferences, beliefs", prompt)
        self.assertIn("/tmp/qa_29_0_0.json", prompt)

    def test_value_prompt_requires_1_to_100_estimate_and_anti_leak_rules(self) -> None:
        args = SimpleNamespace(
            common_template=REPO_ROOT / "prompts" / "05_q_to_b" / "common.md",
            prompts_dir=REPO_ROOT / "prompts" / "05_q_to_b",
        )
        template = load_pre_banger_qa_template(args, "value")

        prompt = render_pre_banger_qa_prompt(
            template,
            "value",
            _seed(),
            [_context_event()],
            Path("/tmp/qa_29_0_0.json"),
            "codex",
            6,
        )

        self.assertIn("QA Type: Pre-Banger Value", prompt)
        self.assertIn("1 to 100", prompt)
        self.assertIn("Keep the question generic", prompt)
        self.assertIn("Do not start questions with a context-preface", prompt)
        self.assertIn("Every answer must start with the numeric estimate", prompt)
        self.assertIn('"value_estimate": 84', prompt)
        self.assertIn("must not say \"value percentile\"", prompt)
        self.assertIn("Do not summarize the hidden artifact", prompt)

    def test_validate_pre_banger_accepts_flat_payload(self) -> None:
        validate_pre_banger_qa_data(_valid_flat_payload(), "qa.json")

    def test_validate_pre_banger_accepts_value_payload(self) -> None:
        validate_pre_banger_qa_data(_valid_flat_payload("value"), "qa.json")

    def test_validate_pre_banger_accepts_threaded_payload(self) -> None:
        validate_pre_banger_qa_data(_valid_threaded_payload(), "qa.json")

    def test_validate_pre_banger_rejects_threaded_payload_over_total_cap(self) -> None:
        data = _valid_threaded_payload()
        for thread in data["threads"]:
            thread["qa_pairs"].append(
                _pair(3, "What extra signal should the assistant read?", "pre_banger_threaded")
            )

        with self.assertRaisesRegex(RuntimeError, "9-10 total"):
            validate_pre_banger_qa_data(data, "qa.json")

    def test_validate_pre_banger_rejects_missing_context_basis(self) -> None:
        data = _valid_flat_payload()
        data["qa_pairs"][0]["question_basis"]["context_event_indexes"] = [2]

        with self.assertRaisesRegex(RuntimeError, "references missing context event index"):
            validate_pre_banger_qa_data(data, "qa.json")

    def test_write_final_pre_banger_qa_consolidates_supported_type_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pre_banger_dir = Path(tmp_dir) / "05_q_to_b"
            curiosity_dir = pre_banger_dir / "curiosity"
            value_dir = pre_banger_dir / "value"
            threaded_dir = pre_banger_dir / "threaded"
            curiosity_dir.mkdir(parents=True)
            value_dir.mkdir(parents=True)
            threaded_dir.mkdir(parents=True)
            (curiosity_dir / "qa_29_0_0.json").write_text(
                json.dumps(_valid_flat_payload()),
                encoding="utf-8",
            )
            (value_dir / "qa_29_0_0.json").write_text(
                json.dumps(_valid_flat_payload("value")),
                encoding="utf-8",
            )
            (threaded_dir / "qa_29_0_0.json").write_text(
                json.dumps(_valid_threaded_payload()),
                encoding="utf-8",
            )

            write_final_pre_banger_qa(
                SimpleNamespace(pre_banger_qa_dir=pre_banger_dir)
            )

            final_data = json.loads((pre_banger_dir / "final_qa.json").read_text())
            self.assertEqual(len(final_data), 3)
            self.assertEqual(
                {item["qa_type"] for item in final_data},
                {"curiosity", "value", "threaded"},
            )

    def test_write_final_pre_banger_qa_uses_scoped_final_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pre_banger_dir = Path(tmp_dir) / "05_q_to_b"
            flat_dir = pre_banger_dir / "timing"
            flat_dir.mkdir(parents=True)
            (flat_dir / "qa_29_0_0.json").write_text(
                json.dumps(_valid_flat_payload("timing")),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                pre_banger_qa_dir=pre_banger_dir,
            )

            write_final_pre_banger_qa(args)

            final_path = pre_banger_dir / "final_qa.json"
            self.assertEqual(final_pre_banger_qa_path(args), final_path)
            self.assertTrue(final_path.exists())

    def test_training_export_flattens_shapes_and_drops_seed_metadata(self) -> None:
        rows = training_rows_from_final_questions(
            [
                {"qa": _valid_flat_payload(), "qa_type": "curiosity"},
                {"qa": _valid_threaded_payload(), "qa_type": "threaded"},
            ]
        )

        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["qa_type"], "curiosity")
        self.assertEqual(rows[0]["category"], "pre_banger_curiosity")
        self.assertNotIn("target_banger", rows[0])
        self.assertNotIn("seed_id", rows[0])
        self.assertEqual(rows[-1]["qa_type"], "threaded")
        self.assertEqual(rows[-1]["thread_id"], 2)

    def test_threaded_prompt_requires_coherent_thread_arcs(self) -> None:
        prompt_text = (REPO_ROOT / "prompts" / "05_q_to_b" / "threaded.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Each thread must have a clear throughline", prompt_text)
        self.assertIn("Thread 0, receptivity", prompt_text)
        self.assertIn("Thread 1, curiosity", prompt_text)
        self.assertIn("Thread 2, self-done", prompt_text)
        self.assertIn("total Q/A pairs across the 3 threads", prompt_text)


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
            "rank_count": 20,
            "rank_percentile": 84.21,
            "value_estimate": 84,
            "timing_reason": "The user is at a high-leverage intervention moment.",
        },
    }


def _ranked_seed(seed_id: str, rank: int, negative_reason: str) -> dict:
    posture = "surface_now" if negative_reason == "none" else "stay_quiet"
    return {
        "rank": rank,
        "seed_id": seed_id,
        "user_value": 8,
        "intervention_value_now": 8 if negative_reason == "none" else 2,
        "intervention_posture": posture,
        "negative_reason": negative_reason,
        "engagement_pull": 7,
        "surprise": 6,
        "personal_relevance": 8,
        "disregard": 4,
        "grounding": 8,
        "self_done_penalty": 2 if negative_reason == "none" else 9,
        "timing_reason": "The timing is assessed for this run.",
        "marginal_value_reason": "The assistant's marginal value is estimated.",
        "self_done_reason": "The user may or may not do it themselves.",
        "future_check": "Future logs are used to calibrate the label.",
    }


def _pair(
    q_id: int,
    question: str,
    category: str,
    answer_basis: str = "H+F",
    verify_at_ts: float = 101.0,
    answer: str = "The assistant should surface help now because it would add timely marginal value.",
) -> dict:
    return {
        "q_id": q_id,
        "question": question,
        "answer": answer,
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
    if qa_type == "value":
        qa_pairs = [
            _pair(
                0,
                "Estimate on a 1 to 100 scale how worthwhile proactive help would be here, and give the reason.",
                category,
                answer="84. The user appears to have enough friction that concise help would likely add value.",
            ),
            _pair(
                1,
                "On a 1 to 100 scale, how much value would help add for the user here, and why?",
                category,
                answer="84. The visible context suggests help could reduce effort without needing to expose the hidden artifact.",
            ),
            _pair(
                2,
                "Estimate how worth surfacing this is on a 1 to 100 scale, with the reason.",
                category,
                answer="84. The user-state signal is strong enough that proactive help would probably be worthwhile.",
            ),
        ]
    else:
        qa_pairs = [
            _pair(0, "What would the user be curious to see right now?", category),
            _pair(1, "Is now a good moment for the assistant to help?", category),
            _pair(2, "What would the user likely do without help?", category),
        ]
    return {
        "qa_type": qa_type,
        "seed_id": "29_0_0",
        "banger_timestamp": 100.0,
        "target_banger": {"suggestion": "hidden"},
        "context_events": [_context_event()],
        "qa_pairs": qa_pairs,
    }


def _valid_threaded_payload() -> dict:
    def thread(thread_id: int, category: str) -> dict:
        return {
            "thread_id": thread_id,
            "qa_pairs": [
                _pair(0, "What is the user's current state?", category),
                _pair(1, "What signal should the assistant read next?", category),
                _pair(2, "What should the assistant infer from that signal?", category),
            ],
        }

    return {
        "qa_type": "threaded",
        "seed_id": "29_0_0",
        "banger_timestamp": 100.0,
        "target_banger": {"suggestion": "hidden"},
        "context_events": [_context_event()],
        "threads": [
            thread(0, "pre_banger_timing"),
            thread(1, "pre_banger_curiosity"),
            thread(2, "pre_banger_disregard"),
        ],
    }


if __name__ == "__main__":
    unittest.main()
