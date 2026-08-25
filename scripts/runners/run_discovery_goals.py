#!/usr/bin/env python3
"""Generate per-interval discovery goals with Codex or Claude."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
