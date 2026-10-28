#!/usr/bin/env python3
"""Download NASA Astronomy Picture of the Day into the Curated folder.

Uses https://api.nasa.gov/planetary/apod.

API key resolution (first wins):
  1. NASA_API_KEY in environment or project .env
  2. nasa_api_key in config.json
  3. DEMO_KEY (shared rate limit — fine for light use)

Fully offline-safe: network failures log and exit non-zero without
affecting the main rotator.

Usage:
  python download_apod.py
  python download_apod.py --count 3
  python download_apod.py --date 2024-07-04
  python download_apod.py --set-today   # download then force wallpaper set
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rotator.apod import fetch_apod
from rotator.config import load_config
from rotator.core import run_daily
from rotator.logging_setup import setup_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download NASA APOD image(s) into Curated (or configured folder).",
    )
    parser.add_argument("-c", "--config", default=None, help="Path to config.json")
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of random APODs (ignored if --date is set)",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Specific APOD date YYYY-MM-DD",
    )
    parser.add_argument(
        "--set-today",
        action="store_true",
        help="After download, force-set today's wallpaper",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    setup_logging(cfg.log_file, level=logging.DEBUG if args.verbose else logging.INFO)

    dest = cfg.apod_save_to or cfg.curated_dir
    count = args.count if args.count is not None else cfg.apod_count
    on_date = date.fromisoformat(args.date) if args.date else None

    paths = fetch_apod(
        api_key=cfg.nasa_api_key,
        count=count,
        dest_dir=dest,
        on_date=on_date,
    )

    if not paths:
        print("No APOD images downloaded (offline, rate-limited, or video-only day).")
        return 1

    for p in paths:
        print(f"Saved: {p}")

    if args.set_today:
        result = run_daily(cfg, force=True)
        print(result.message)
        return 0 if result.success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
