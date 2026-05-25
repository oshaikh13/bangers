from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from viewer.app import create_app  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Serve a local web viewer for discovery pipeline outputs."
    )
    parser.add_argument(
        "--discovery-dir",
        type=Path,
        help=(
            "Discovery run directory to open by default. "
            "Defaults to the most recently modified discovery_* directory."
        ),
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind. Defaults to 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind. Defaults to 8000.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    discovery_dir = args.discovery_dir.resolve() if args.discovery_dir else None
    if discovery_dir is not None and not discovery_dir.is_dir():
        raise SystemExit(f"discovery dir not found: {discovery_dir}")

    app = create_app(default_discovery_dir=discovery_dir)
    print(f"Discovery viewer running at http://{args.host}:{args.port}")
    if app.state.default_run:
        print(f"Default run: {app.state.default_run}")
    else:
        print("No discovery_* directories found yet.")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
