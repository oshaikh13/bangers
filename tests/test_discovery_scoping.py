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
    def test_interval_range_run_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            args = parse_args(
                [
                    "--combine",
                    "--discovery-dir",
                    tmp_dir,
                    "--interval-range",
                    "2-42",
                    "--run-id",
                    "run-a",
                ]
            )
            base = Path(tmp_dir).resolve() / "intervals_2-42" / "run-a"

            self.assertEqual(args.scope_slug, "intervals_2-42")
            self.assertEqual(args.run_root, base)
            self.assertEqual(args.goals_dir, base / "02_goals" / "goals")
            self.assertEqual(args.combined_dir, base / "02_goals" / "combined")
            self.assertEqual(args.bridges_dir, base / "02_goals" / "bridges")
            self.assertEqual(args.suggestion_inputs_dir, base / "03_bangers")
            self.assertEqual(args.bangers_dir, base / "03_bangers")
            self.assertEqual(args.questions_dir, base / "04_b_to_q")

    def test_goals_without_run_id_creates_timestamp_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            args = parse_args(
                [
                    "--discovery-dir",
                    tmp_dir,
                    "--interval-range",
                    "0-1",
                ]
            )

            self.assertEqual(args.scope_slug, "intervals_0-1")
            self.assertRegex(args.run_id, r"^\d{8}T\d{6}Z$")
            self.assertEqual(args.run_root.name, args.run_id)
            self.assertEqual(args.run_root.parent.name, "intervals_0-1")

    def test_downstream_without_run_id_uses_latest_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            scope_dir = Path(tmp_dir) / "intervals_0-1"
            (scope_dir / "20260101T000000Z").mkdir(parents=True)
            (scope_dir / "20260102T000000Z").mkdir()

            args = parse_args(
                [
                    "--questions",
                    "--discovery-dir",
                    tmp_dir,
                    "--interval-range",
                    "0-1",
                ]
            )

            self.assertEqual(args.run_id, "20260102T000000Z")
            self.assertEqual(args.run_root, (scope_dir / "20260102T000000Z").resolve())

    def test_combine_reads_only_current_run_goals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir) / "intervals_0-1" / "run-a"
            goals_dir = base / "02_goals" / "goals"
            other_goals_dir = Path(tmp_dir) / "intervals_0-1" / "run-b" / "02_goals" / "goals"
            goals_dir.mkdir(parents=True)
            other_goals_dir.mkdir(parents=True)
            (goals_dir / "goal_0.json").write_text("[]", encoding="utf-8")
            (other_goals_dir / "goal_1.json").write_text("[]", encoding="utf-8")

            args = parse_args(
                [
                    "--combine",
                    "--discovery-dir",
                    tmp_dir,
                    "--interval-range",
                    "0-1",
                    "--run-id",
                    "run-a",
                ]
            )

            self.assertEqual(
                [path.name for path in combine_goal_files(args)],
                ["goal_0.json"],
            )


if __name__ == "__main__":
    unittest.main()
