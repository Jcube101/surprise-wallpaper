#!/usr/bin/env python3
"""Stable entry point for Windows Task Scheduler.

Always uses smart logic: skip if wallpaper was already set today (IST / config TZ).
Use set_today.py when you want to force a re-set.

Usage:
  python run_rotator.py
  python run_rotator.py --force
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rotator.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
