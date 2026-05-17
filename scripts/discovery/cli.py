from __future__ import annotations

import argparse
from pathlib import Path

from .paths import (
    DEFAULT_INTERVAL_MINUTES,
    DEFAULT_TEMPLATE,
    REPO_ROOT,
    default_candidates_dir,
    default_intervals_path,
)
from .runner import run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run prompts/discovery.md against interval JSONL rows."
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
        default=str(DEFAULT_TEMPLATE),
        help="Prompt template containing {candidate_row} and {interval_index}.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Working repository passed to the agent CLI.",
    )
    parser.add_argument(
        "--candidates-dir",
        help="Directory where candidate_<interval_index>.json files are expected.",
    )
    parser.add_argument(
        "--run-log",
        help="JSONL run ledger written by this runner. Defaults inside --candidates-dir.",
    )
    parser.add_argument(
        "--interval-indexes",
        help="Comma-separated interval indexes or ranges to run, e.g. `0,3,10-12`.",
    )
    parser.add_argument("--start", type=int, default=0, help="Start offset.")
    parser.add_argument("--limit", type=int, help="Maximum number of rows to run.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even if candidate_<interval_index>.json already exists.",
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
        help="Continue to later intervals if one agent run fails.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of intervals to run concurrently. Defaults to 1.",
    )
    parser.add_argument(
        "--no-isolate-agent-workdir",
        action="store_true",
        help=(
            "Run the agent in the real repo. By default each run sees only a "
            "temporary copy of logs-indexed and an empty output directory."
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
        default="xhigh",
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
        default="xhigh",
        choices=("low", "medium", "high", "xhigh", "max"),
        help="Effort level passed to Claude.",
    )
    group.add_argument(
        "--claude-permission-mode",
        default="acceptEdits",
        choices=("default", "acceptEdits", "plan", "auto", "dontAsk", "bypassPermissions"),
        help="Permission mode for Claude. acceptEdits lets Claude write candidate files.",
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
    if args.startup_progress_every < 0:
        raise SystemExit("--startup-progress-every must be non-negative")

    args.repo_root = Path(args.repo_root).resolve()
    args.template = Path(args.template).resolve()

    if args.intervals is None:
        args.intervals = default_intervals_path(interval_minutes)

    if args.candidates_dir:
        args.candidates_dir = Path(args.candidates_dir)
    else:
        args.candidates_dir = default_candidates_dir(args.provider, interval_minutes)

    if args.run_log:
        args.run_log = Path(args.run_log)
    else:
        args.run_log = args.candidates_dir / f"{args.provider}_exec_runs.jsonl"

    if args.claude_stream:
        args.claude_output_format = "stream-json"
        args.claude_verbose = True
        args.claude_include_partial_messages = True

    if args.claude_include_partial_messages and args.claude_output_format != "stream-json":
        raise SystemExit("--claude-include-partial-messages requires --claude-output-format stream-json")

    args.intervals = args.intervals.resolve()
    args.candidates_dir = args.candidates_dir.resolve()
    args.run_log = args.run_log.resolve()


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))
