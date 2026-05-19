#!/usr/bin/env python3
"""Combine discovery candidate JSON files with Codex or Claude."""

from __future__ import annotations

import sys

from discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["--combine", *sys.argv[1:]]))
