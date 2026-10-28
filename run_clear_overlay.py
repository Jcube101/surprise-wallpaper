#!/usr/bin/env python3
"""Clear a fullscreen Windows Input Experience window, if one is up.

Task Scheduler runs this about once a minute while you are logged on.
It does not change the wallpaper. It logs only when it actually hides a window.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rotator.config import load_config
from rotator.windows_wallpaper import dismiss_blocking_input_overlay


def _file_logger(log_file: Path) -> logging.Logger:
    """Log to the rotator file only.

    The scheduled task uses pythonw.exe, which has no console, so stdout
    is missing and a console log handler would throw.
    """
    log = logging.getLogger("run_clear_overlay")
    log.setLevel(logging.INFO)
    log.propagate = False
    if any(isinstance(handler, logging.FileHandler) for handler in log.handlers):
        return log
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file, encoding="utf-8")
    except OSError:
        return log
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    log.addHandler(handler)
    return log


def main() -> int:
    cfg = load_config()
    log = _file_logger(cfg.log_file)
    try:
        hidden = dismiss_blocking_input_overlay()
    except Exception:
        log.exception("clear-overlay failed")
        return 1
    if hidden:
        log.info(
            "Hid %s fullscreen Windows Input Experience window(s) covering the desktop",
            hidden,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
