#!/usr/bin/env python3
"""Manual 'set today' — force-set today's wallpaper (ignores .last_set.txt).

Usage:
  python set_today.py
  python set_today.py --dry-run
  python set_today.py -c path/to/config.json
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running from any CWD when project root is on sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rotator.config import load_config
from rotator.core import run_daily
from rotator.logging_setup import setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Force-set today's Grok / Curated wallpaper.",
    )
    parser.add_argument("-c", "--config", default=None, help="Path to config.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which image would be used without applying it",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    setup_logging(cfg.log_file, level=logging.DEBUG if args.verbose else logging.INFO)

    result = run_daily(cfg, force=True, dry_run=args.dry_run)
    print(result.message)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
