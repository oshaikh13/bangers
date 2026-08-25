#!/usr/bin/env python3
"""Run 05_q_to_b pre-banger QA generation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery.pre_banger_qa import main


if __name__ == "__main__":
    raise SystemExit(main())
