#!/usr/bin/env python3
"""Midnight entry: generate today's themed wallpaper if missing, else set.

Used by Task Scheduler (GrokWallpaper-DailyMidnight).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rotator.config import load_config
from rotator.core import run_daily
from rotator.daily import generate_daily
from rotator.logging_setup import setup_logging


def main() -> int:
    cfg = load_config()
    setup_logging(cfg.log_file, level=logging.INFO)
    log = logging.getLogger("run_daily_generate")

    result = generate_daily(cfg, force=False, set_wallpaper=True)
    log.info(result.message)
    print(result.message)

    if not result.success:
        # Wake-from-sleep catch-up hits the same failures. Auto-dismiss so a
        # locked session cannot pin this task until the 25-minute kill.
        from rotator.notify import alert_generation_failure

        alert_generation_failure(result.message, timeout_ms=5 * 60 * 1000)
        return 1

    if result.skipped:
        # Ensure desktop is set even if we skipped generate
        set_result = run_daily(cfg, force=False)
        print(set_result.message)
        return 0 if set_result.success else 1

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
