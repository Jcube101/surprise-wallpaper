"""CLI entry: python -m rotator [options]

Default action: smart daily set (skip if already set today).
"""

from __future__ import annotations

import argparse
import logging
import sys

from rotator import __version__
from rotator.config import load_config
from rotator.core import run_daily
from rotator.logging_setup import setup_logging


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rotator",
        description="Grok Surprise Wallpaper Rotator — set today's desktop wallpaper.",
    )
    p.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to config.json (default: project root)",
    )
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Set wallpaper even if already set today",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Select image only; do not change wallpaper or state",
    )
    p.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Debug logging",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)

    level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(cfg.log_file, level=level)

    result = run_daily(cfg, force=args.force, dry_run=args.dry_run)

    if result.skipped:
        return 0
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
