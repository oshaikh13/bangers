#!/usr/bin/env python3
"""Generate question/answer pairs for discovered banger opportunities."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["--questions", *sys.argv[1:]]))
