#!/usr/bin/env python3
"""Generate proactive suggestions for combined discovery goals."""

from __future__ import annotations

import sys

from discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["--bangers", *sys.argv[1:]]))
