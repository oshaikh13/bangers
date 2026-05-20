#!/usr/bin/env python3
"""Generate question/answer pairs for discovered banger opportunities."""

from __future__ import annotations

import sys

from discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["--questions", *sys.argv[1:]]))
