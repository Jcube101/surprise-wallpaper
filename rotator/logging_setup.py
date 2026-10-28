"""Central logging setup — file + console, graceful if log dir is missing."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(log_file: Path | None = None, level: int = logging.INFO) -> None:
    """Configure root logger with console handler and optional rotating-style file.

    Uses a simple FileHandler (append). Creates parent dirs when possible.
    If the file cannot be opened, falls back to console-only (offline/locked disk).
    """
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. re-import); just bump level
        root.setLevel(level)
        return

    root.setLevel(level)
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    if log_file is None:
        return

    try:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError as e:
        root.warning("Could not open log file %s (%s); console only", log_file, e)
