from __future__ import annotations

import argparse
from pathlib import Path

from .paths import (
    DEFAULT_BANGERS_TEMPLATE,
    DEFAULT_BRIDGES_TEMPLATE,
    DEFAULT_COMBINE_TEMPLATE,
    DEFAULT_DISCOVERY_TEMPLATE,
    DEFAULT_INTERVAL_MINUTES,
    DEFAULT_QUESTIONS_TEMPLATE,
    REPO_ROOT,
    default_discovery_dir,
    default_intervals_path,
)
from .runner import (
    DEFAULT_QUESTIONS_SAMPLE_FRACTION,
    DEFAULT_QUESTIONS_SAMPLE_SEED,
    run,
)
from .scoping import latest_run_id, new_run_id, run_root_for, scope_slug


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the discovery pipeline: goals, combine, bridges, bangers, questions."
        )
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--combine",
        action="store_true",
        help=(
            "Run prompts/02_goals/combine.md over 02_goals/goals and write "
            "02_goals/combined/combined.json."
        ),
    )
    mode_group.add_argument(
        "--bridges",
        action="store_true",
        help=(
            "Run prompts/02_goals/bridges.md over combined.json and write "
            "02_goals/bridges/bridges.json."
        ),
    )
    mode_group.add_argument(
        "--questions",
        action="store_true",
        help=(
            "Run prompts/04_b_to_q/questions.md once per selected banger "
            "opportunity and write question/answer JSON files."
        ),
    )
    mode_group.add_argument(
        "--bangers",
        action="store_true",
        help=(
            "Run prompts/03_bangers/bangers.md once per selected banger input "
            "and write suggestion JSON files."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=("codex", "claude"),
        default="codex",
        help="Agent CLI used for each discovery run.",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        help=(
            "Interval size used to derive default paths. For example, 30 uses "
            "data/log_intervals_30m.jsonl."
        ),
    )
    parser.add_argument(
        "--intervals",
        type=Path,
        help="Input JSONL of interval rows. Defaults to data/log_intervals_<minutes>m.jsonl.",
    )
    parser.add_argument(
        "--template",
        help=(
            "Prompt template. Defaults to the numbered prompt for the selected "
            "stage."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Working repository passed to the agent CLI.",
    )
    parser.add_argument(
        "--discovery-dir",
        help="Discovery run directory. Defaults to discovery_<provider>_<minutes>m.",
    )
    parser.add_argument(
        "--interval-range",
        required=True,
        help="Inclusive interval range to run, e.g. `0-42`.",
    )
    parser.add_argument(
        "--run-id",
        help=(
            "Versioned run id. Defaults to a new timestamp for 02_goals and "
            "the latest run for downstream stages."
        ),
    )
    parser.add_argument(
        "--run-root",
        help="Explicit versioned run root. Overrides --run-id path derivation.",
    )
    parser.add_argument(
        "--goals-dir",
        help="Goals output/input directory. Defaults to <run-root>/02_goals/goals.",
    )
    parser.add_argument(
        "--combined-dir",
        help="Combined goals directory. Defaults to <run-root>/02_goals/combined.",
    )
    parser.add_argument(
        "--bridges-dir",
        help="Bridge goals directory. Defaults to <run-root>/02_goals/bridges.",
    )
    parser.add_argument(
        "--suggestion-inputs-dir",
        help=(
            "Banger suggestion input directory. Defaults to <run-root>/03_bangers."
        ),
    )
    parser.add_argument(
        "--bangers-dir",
        help="Bangers directory. Defaults to <run-root>/03_bangers.",
    )
    parser.add_argument(
        "--questions-dir",
        help="Questions directory. Defaults to <run-root>/04_b_to_q.",
    )
    parser.add_argument(
        "--run-log",
        help="JSONL run ledger written by this runner. Defaults inside --run-root.",
    )
    parser.add_argument(
        "--banger-input-indexes",
        dest="banger_input_indexes",
        help=(
            "With --bangers or --questions, comma-separated zero-based "
            "indexes or ranges in 03_bangers/inputs.json to run, "
            "e.g. `0,3,10-12`."
        ),
    )
    parser.add_argument(
        "--combined-indexes",
        dest="banger_input_indexes",
        help=(
            "Comma-separated zero-based banger input indexes or ranges."
        ),
    )
    parser.add_argument("--start", type=int, default=0, help="Start offset.")
    parser.add_argument("--limit", type=int, help="Maximum number of rows to run.")
    parser.add_argument(
        "--questions-sample-fraction",
        type=float,
        default=DEFAULT_QUESTIONS_SAMPLE_FRACTION,
        help=(
            "With --questions, randomly sample this fraction of selected banger "
            "opportunities before applying --limit. Defaults to 0.10; use 1.0 "
            "to generate questions for every selected opportunity."
        ),
    )
    parser.add_argument(
        "--questions-sample-seed",
        default=DEFAULT_QUESTIONS_SAMPLE_SEED,
        help=(
            "With --questions, seed used for deterministic random sampling. "
            "Change this to pick a different subset."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Run even if the expected output already exists "
            "(goal_<interval_index>.json, combined.json, banger files, "
            "or question files)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands and prompt previews without invoking the agent CLI.",
    )
    parser.add_argument(
        "--print-prompt",
        action="store_true",
        help="With --dry-run, print full rendered prompts instead of previews.",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue to later selected items if one agent run fails.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of selected items to run concurrently. Defaults to 1.",
    )
    parser.add_argument(
        "--banger-batch-size",
        type=int,
        default=1,
        help=(
            "With --bangers, number of banger inputs to include in each "
            "agent run. Defaults to 1 for one range-named output file per run."
        ),
    )
    parser.add_argument(
        "--no-isolate-agent-workdir",
        action="store_true",
        help=(
            "Run the agent in the real repo. By default each run uses a "
            "temporary workdir with only the stage inputs it needs; stages "
            "that inspect logs see logs-indexed and an empty output directory."
        ),
    )
    parser.add_argument(
        "--keep-agent-workdirs",
        action="store_true",
        help="Do not delete temporary isolated workdirs after each run.",
    )
    parser.add_argument(
        "--screenshot-link-mode",
        choices=("hardlink", "symlink"),
        default="hardlink",
        help=(
            "How isolated workdirs expose logs-indexed/screenshots. hardlink keeps "
            "files inside the workdir; symlink is faster but points outside it."
        ),
    )
    parser.add_argument(
        "--startup-progress-every",
        type=int,
        default=5000,
        help=(
            "Minimum screenshot files between tqdm startup progress refreshes. "
            "Use 0 to let tqdm choose."
        ),
    )
    add_codex_args(parser)
    add_claude_args(parser)
    return parser


def add_codex_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("Codex options")
    group.add_argument("--codex-bin", default="codex", help="Codex executable.")
    group.add_argument(
        "--codex-model",
        default="gpt-5.5",
        help="Model passed to `codex exec -m`.",
    )
    group.add_argument(
        "--codex-reasoning-effort",
        default="high",
        help="Reasoning effort passed to Codex.",
    )
    group.add_argument(
        "--codex-sandbox",
        default="workspace-write",
        choices=("read-only", "workspace-write", "danger-full-access"),
        help="Sandbox mode for Codex.",
    )
    group.add_argument(
        "--codex-ephemeral",
        action="store_true",
        help="Pass --ephemeral to codex exec.",
    )
    group.add_argument(
        "--codex-ignore-user-config",
        action="store_true",
        help="Pass --ignore-user-config to codex exec.",
    )
    group.add_argument(
        "--codex-ignore-rules",
        action="store_true",
        help="Pass --ignore-rules to codex exec.",
    )
    group.add_argument(
        "--codex-json-events",
        action="store_true",
        help="Pass --json to codex exec.",
    )


def add_claude_args(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group("Claude options")
    group.add_argument("--claude-bin", default="claude", help="Claude executable.")
    group.add_argument(
        "--claude-model",
        help="Model passed to Claude with --model. Omit to use Claude's configured default.",
    )
    group.add_argument(
        "--claude-effort",
        default="high",
        choices=("low", "medium", "high", "xhigh", "max"),
        help="Effort level passed to Claude.",
    )
    group.add_argument(
        "--claude-permission-mode",
        default="auto",
        choices=("default", "acceptEdits", "plan", "auto", "dontAsk", "bypassPermissions"),
        help=(
            "Permission mode for Claude. auto lets Claude run Bash, Read, and "
            "Write unattended so it can explore logs and write output files."
        ),
    )
    group.add_argument(
        "--claude-output-format",
        default=None,
        choices=("text", "json", "stream-json"),
        help=(
            "Output format passed to Claude. Defaults to stream-json while "
            "--claude-stream is enabled."
        ),
    )
    group.add_argument(
        "--claude-max-turns",
        type=int,
        help="Optional --max-turns limit for Claude print mode.",
    )
    group.add_argument(
        "--claude-append-system-prompt-file",
        help="Optional file passed with --append-system-prompt-file.",
    )
    group.add_argument(
        "--claude-allowed-tools",
        action="append",
        default=[],
        help="Repeatable --allowedTools value passed to Claude.",
    )
    group.add_argument(
        "--claude-stream",
        action="store_true",
        default=True,
        help="Stream Claude JSON events with verbose partial message deltas.",
    )
    group.add_argument(
        "--no-claude-stream",
        dest="claude_stream",
        action="store_false",
        help="Use Claude's non-streaming output mode unless --claude-output-format is set.",
    )
    group.add_argument(
        "--claude-verbose",
        action="store_true",
        help="Pass --verbose to Claude.",
    )
    group.add_argument(
        "--claude-include-partial-messages",
        action="store_true",
        help="Pass --include-partial-messages to Claude. Requires stream-json output.",
    )
    group.add_argument(
        "--claude-bare",
        action="store_true",
        help=(
            "Pass --bare to Claude. Useful for CI, but requires ANTHROPIC_API_KEY "
            "or an apiKeyHelper in --settings."
        ),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    normalize_args(args)
    return args


def normalize_args(args: argparse.Namespace) -> None:
    interval_minutes = args.interval_minutes or DEFAULT_INTERVAL_MINUTES
    if interval_minutes <= 0:
        raise SystemExit("--interval-minutes must be greater than 0")
    if args.jobs <= 0:
        raise SystemExit("--jobs must be greater than 0")
    if args.banger_batch_size <= 0:
        raise SystemExit("--banger-batch-size must be greater than 0")
    if args.questions_sample_fraction <= 0 or args.questions_sample_fraction > 1:
        raise SystemExit("--questions-sample-fraction must be greater than 0 and at most 1")
    if args.startup_progress_every < 0:
        raise SystemExit("--startup-progress-every must be non-negative")
    if args.banger_input_indexes and not (args.questions or args.bangers):
        raise SystemExit("--banger-input-indexes requires --bangers or --questions")

    args.repo_root = Path(args.repo_root).resolve()
    if args.questions:
        default_template = DEFAULT_QUESTIONS_TEMPLATE
    elif args.bangers:
        default_template = DEFAULT_BANGERS_TEMPLATE
    elif args.bridges:
        default_template = DEFAULT_BRIDGES_TEMPLATE
    elif args.combine:
        default_template = DEFAULT_COMBINE_TEMPLATE
    else:
        default_template = DEFAULT_DISCOVERY_TEMPLATE
    args.template = Path(args.template or default_template).resolve()

    if args.intervals is None:
        args.intervals = default_intervals_path(interval_minutes)

    args.interval_minutes = interval_minutes
    if args.discovery_dir:
        args.discovery_dir = Path(args.discovery_dir)
    else:
        args.discovery_dir = default_discovery_dir(args.provider, interval_minutes)

    args.scope_slug = scope_slug(args)
    if args.run_root:
        args.run_root = Path(args.run_root)
        args.run_id = args.run_id or args.run_root.name
    else:
        if args.run_id:
            run_id = args.run_id
        elif not (args.combine or args.bridges or args.bangers or args.questions):
            run_id = new_run_id()
        else:
            run_id = latest_run_id(args.discovery_dir, args.scope_slug)
        args.run_id = run_id
        args.run_root = run_root_for(args.discovery_dir, args.scope_slug, run_id)

    args.goals_dir = (
        Path(args.goals_dir)
        if args.goals_dir
        else args.run_root / "02_goals" / "goals"
    )
    args.combined_dir = (
        Path(args.combined_dir)
        if args.combined_dir
        else args.run_root / "02_goals" / "combined"
    )
    args.bridges_dir = (
        Path(args.bridges_dir)
        if args.bridges_dir
        else args.run_root / "02_goals" / "bridges"
    )
    args.suggestion_inputs_dir = (
        Path(args.suggestion_inputs_dir)
        if args.suggestion_inputs_dir
        else args.run_root / "03_bangers"
    )
    args.bangers_dir = (
        Path(args.bangers_dir)
        if args.bangers_dir
        else args.run_root / "03_bangers"
    )
    args.questions_dir = (
        Path(args.questions_dir)
        if args.questions_dir
        else args.run_root / "04_b_to_q"
    )

    if args.run_log:
        args.run_log = Path(args.run_log)
    else:
        args.run_log = args.run_root / f"{args.provider}_exec_runs.jsonl"

    if args.claude_stream:
        args.claude_output_format = "stream-json"
        args.claude_verbose = True
        args.claude_include_partial_messages = True

    if args.claude_include_partial_messages and args.claude_output_format != "stream-json":
        raise SystemExit("--claude-include-partial-messages requires --claude-output-format stream-json")

    args.intervals = args.intervals.resolve()
    args.discovery_dir = args.discovery_dir.resolve()
    args.run_root = args.run_root.resolve()
    args.goals_dir = args.goals_dir.resolve()
    args.combined_dir = args.combined_dir.resolve()
    args.bridges_dir = args.bridges_dir.resolve()
    args.suggestion_inputs_dir = args.suggestion_inputs_dir.resolve()
    args.questions_dir = args.questions_dir.resolve()
    args.bangers_dir = args.bangers_dir.resolve()
    args.run_log = args.run_log.resolve()


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))
