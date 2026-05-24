#!/usr/bin/env python3
"""Generate cross-goal bridge opportunities from combined discovery goals."""

from __future__ import annotations

import sys

from discovery.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["--bridges", *sys.argv[1:]]))
