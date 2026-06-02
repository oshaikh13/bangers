from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from discovery.cli import parse_args
from discovery.runner import combine_goal_files


class DiscoveryScopingTests(unittest.TestCase):
    def test_day_scoped_stage_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            args = parse_args(["--combine", "--discovery-dir", tmp_dir, "--day", "1"])
            base = Path(tmp_dir).resolve()

            self.assertEqual(args.scope_slug, "days_1")
            self.assertEqual(args.goals_dir, base / "01_goals" / "days_1")
            self.assertEqual(args.combined_dir, base / "02a_combined" / "days_1")
            self.assertEqual(args.bridges_dir, base / "02b_bridges" / "days_1")
            self.assertEqual(
                args.suggestion_inputs_dir,
                base / "02c_suggestion_inputs" / "days_1",
            )
            self.assertEqual(args.bangers_dir, base / "03_bangers" / "days_1")
            self.assertEqual(args.questions_dir, base / "04_questions" / "days_1")

    def test_interval_scoped_stage_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            args = parse_args(
                [
                    "--questions",
                    "--discovery-dir",
                    tmp_dir,
                    "--interval-indexes",
                    "2-42",
                ]
            )
            base = Path(tmp_dir).resolve()

            self.assertEqual(args.scope_slug, "intervals_2-42")
            self.assertEqual(args.bangers_dir, base / "03_bangers" / "intervals_2-42")
            self.assertEqual(args.questions_dir, base / "04_questions" / "intervals_2-42")

    def test_global_paths_stay_at_stage_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            args = parse_args(["--bangers", "--discovery-dir", tmp_dir])
            base = Path(tmp_dir).resolve()

            self.assertEqual(args.scope_slug, "global")
            self.assertEqual(args.goals_dir, base / "01_goals")
            self.assertEqual(args.bangers_dir, base / "03_bangers")

    def test_day_combine_reads_only_that_day_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "01_goals" / "days_0").mkdir(parents=True)
            (base / "01_goals" / "days_1").mkdir(parents=True)
            (base / "01_goals" / "days_0" / "goal_0.json").write_text("[]")
            (base / "01_goals" / "days_1" / "goal_2.json").write_text("[]")

            args = parse_args(["--combine", "--discovery-dir", tmp_dir, "--day", "1"])

            self.assertEqual(
                [path.name for path in combine_goal_files(args)],
                ["goal_2.json"],
            )

    def test_global_combine_reads_all_day_scoped_goals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "01_goals").mkdir(parents=True)
            (base / "01_goals" / "goal_99.json").write_text("[]")
            (base / "01_goals" / "days_0").mkdir()
            (base / "01_goals" / "days_1").mkdir()
            (base / "01_goals" / "days_0" / "goal_0.json").write_text("[]")
            (base / "01_goals" / "days_1" / "goal_2.json").write_text("[]")

            args = parse_args(["--combine", "--discovery-dir", tmp_dir])

            self.assertEqual(
                [path.name for path in combine_goal_files(args)],
                ["goal_0.json", "goal_2.json"],
            )


if __name__ == "__main__":
    unittest.main()
