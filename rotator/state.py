"""Persist last-successful wallpaper date to avoid duplicate daily sets."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)


def today_in_tz(timezone: str) -> date:
    """Return today's calendar date in the given IANA timezone (e.g. Asia/Kolkata)."""
    from datetime import datetime

    try:
        tz = ZoneInfo(timezone)
    except Exception:
        log.warning("Unknown timezone %r; falling back to Asia/Kolkata", timezone)
        tz = ZoneInfo("Asia/Kolkata")
    return datetime.now(tz).date()


def read_last_set(state_file: Path) -> date | None:
    """Read YYYY-MM-DD from state file. Returns None if missing or invalid."""
    try:
        if not state_file.is_file():
            return None
        text = state_file.read_text(encoding="utf-8").strip()
        if not text:
            return None
        # Allow optional extra lines (path, comments) — first line is the date
        first = text.splitlines()[0].strip()
        return date.fromisoformat(first)
    except (OSError, ValueError) as e:
        log.warning("Could not read state file %s: %s", state_file, e)
        return None


def read_last_image_path(state_file: Path) -> Path | None:
    """Second line of state file, if present and exists on disk."""
    try:
        if not state_file.is_file():
            return None
        lines = state_file.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) < 2:
            return None
        p = Path(lines[1].strip())
        return p if p.is_file() else None
    except OSError as e:
        log.warning("Could not read last image path from %s: %s", state_file, e)
        return None


def write_last_set(state_file: Path, day: date, image_path: Path | None = None) -> None:
    """Write today's date (and optional image path) after a successful set."""
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        lines = [day.isoformat()]
        if image_path is not None:
            lines.append(str(image_path.resolve()))
        state_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        log.debug("Wrote state: %s -> %s", day.isoformat(), state_file)
    except OSError as e:
        log.error("Failed to write state file %s: %s", state_file, e)


def already_set_today(state_file: Path, timezone: str) -> bool:
    """True if wallpaper was already successfully set for today (in configured TZ)."""
    last = read_last_set(state_file)
    if last is None:
        return False
    return last == today_in_tz(timezone)
