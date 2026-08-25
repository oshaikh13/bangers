#!/usr/bin/env python3
"""Run 03_bangers seed ranking over generated banger seeds."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from discovery.pre_banger_qa import main


if __name__ == "__main__":
    raise SystemExit(main(["--rank-only", *sys.argv[1:]]))
