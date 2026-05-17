from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


CLAUDE_MODEL_ALIASES = {
    "4.7": "claude-opus-4-7",
    "opus-4.7": "claude-opus-4-7",
}


@dataclass(frozen=True)
class ProviderCommand:
    name: str
    command: list[str]
    prompt_via_stdin: bool
    model: str | None
    effort: str | None
    sandbox: str | None


def build_provider_command(
    args: argparse.Namespace,
    repo_root: Path | None = None,
) -> ProviderCommand:
    if args.provider == "codex":
        return build_codex_command(args, repo_root or args.repo_root)
    if args.provider == "claude":
        return build_claude_command(args, repo_root or args.repo_root)
    raise SystemExit(f"unsupported provider: {args.provider}")


def build_codex_command(args: argparse.Namespace, repo_root: Path) -> ProviderCommand:
    command = [
        args.codex_bin,
        "exec",
        "-m",
        args.codex_model,
        "-c",
        f'model_reasoning_effort="{args.codex_reasoning_effort}"',
        "--sandbox",
        args.codex_sandbox,
        "--cd",
        str(repo_root),
    ]

    if args.codex_ephemeral:
        command.append("--ephemeral")
    if args.codex_ignore_user_config:
        command.append("--ignore-user-config")
    if args.codex_ignore_rules:
        command.append("--ignore-rules")
    if args.codex_json_events:
        command.append("--json")

    command.append("-")
    return ProviderCommand(
        name="codex",
        command=command,
        prompt_via_stdin=True,
        model=args.codex_model,
        effort=args.codex_reasoning_effort,
        sandbox=args.codex_sandbox,
    )


def build_claude_command(args: argparse.Namespace, repo_root: Path) -> ProviderCommand:
    command = [args.claude_bin]
    if args.claude_bare:
        command.append("--bare")
    claude_model = (
        CLAUDE_MODEL_ALIASES.get(args.claude_model, args.claude_model)
        if args.claude_model
        else None
    )
    if claude_model:
        command.extend(["--model", claude_model])
    if args.claude_effort:
        command.extend(["--effort", args.claude_effort])
    if args.claude_permission_mode:
        command.extend(["--permission-mode", args.claude_permission_mode])
    if args.claude_output_format:
        command.extend(["--output-format", args.claude_output_format])
    if args.claude_verbose:
        command.append("--verbose")
    if args.claude_include_partial_messages:
        command.append("--include-partial-messages")
    if args.claude_max_turns is not None:
        command.extend(["--max-turns", str(args.claude_max_turns)])
    if args.claude_append_system_prompt_file:
        command.extend(
            [
                "--append-system-prompt-file",
                str(Path(args.claude_append_system_prompt_file)),
            ]
        )
    for allowed_tool in args.claude_allowed_tools:
        command.extend(["--allowedTools", allowed_tool])

    command.append("-p")
    return ProviderCommand(
        name="claude",
        command=command,
        prompt_via_stdin=True,
        model=claude_model,
        effort=args.claude_effort,
        sandbox=args.claude_permission_mode,
    )
