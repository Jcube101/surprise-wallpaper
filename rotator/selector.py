"""Select today's wallpaper from Grok_Daily (primary) or Curated (secondary)."""

from __future__ import annotations

import logging
import random
import re
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

# Matches YYYY-MM-DD anywhere in the filename (not only a full date stem)
_DATE_IN_NAME = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")


def list_images(folder: Path, extensions: frozenset[str]) -> list[Path]:
    """Return image files in *folder* (non-recursive). Missing folder → empty list."""
    if not folder.is_dir():
        log.debug("Folder missing or not a directory: %s", folder)
        return []

    images: list[Path] = []
    try:
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in extensions:
                images.append(p)
    except OSError as e:
        log.warning("Cannot list %s: %s", folder, e)
        return []

    return images


def prefer_date_match(images: list[Path], day: date) -> Path | None:
    """Prefer a file whose name contains *day* as YYYY-MM-DD; else most recent mtime."""
    if not images:
        return None

    day_str = day.isoformat()  # YYYY-MM-DD
    dated = [p for p in images if day_str in p.name]

    if dated:
        # If several match today's date, pick the newest by mtime
        chosen = max(dated, key=_mtime_key)
        log.info("Date match for %s: %s", day_str, chosen.name)
        return chosen

    chosen = max(images, key=_mtime_key)
    log.info(
        "No file with %s in name; using most recent: %s",
        day_str,
        chosen.name,
    )
    return chosen


def _mtime_key(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def latest_image(folder: Path, extensions: frozenset[str]) -> Path | None:
    """Newest image by mtime in *folder* (non-recursive)."""
    images = list_images(folder, extensions)
    if not images:
        return None
    return max(images, key=_mtime_key)


def random_image(
    folders: list[Path],
    extensions: frozenset[str],
    *,
    rng: random.Random | None = None,
) -> Path | None:
    """Uniform pick among all images in *folders* (non-recursive)."""
    rng = rng or random.Random()
    pool: list[Path] = []
    for folder in folders:
        pool.extend(list_images(folder, extensions))
    if not pool:
        return None
    return rng.choice(pool)


def library_images(
    folders: list[Path],
    extensions: frozenset[str],
) -> list[Path]:
    """All images from *folders*, sorted by name (stable cycle order)."""
    pool: list[Path] = []
    for folder in folders:
        pool.extend(list_images(folder, extensions))
    # Sort by resolved path string for deterministic "next"
    return sorted(pool, key=lambda p: str(p.resolve()).lower())


def next_image(
    folders: list[Path],
    extensions: frozenset[str],
    current: Path | None = None,
    *,
    step: int = 1,
) -> Path | None:
    """Return the next image after *current* in sorted library (wraps around).

    *step* may be negative for previous. If *current* is missing/unknown, returns
    the first (or last if step < 0) image.
    """
    pool = library_images(folders, extensions)
    if not pool:
        return None
    if current is None:
        return pool[0] if step >= 0 else pool[-1]

    try:
        cur = current.resolve()
    except OSError:
        cur = current

    idx = None
    for i, p in enumerate(pool):
        try:
            if p.resolve() == cur:
                idx = i
                break
        except OSError:
            if p == current or p.name == current.name:
                idx = i
                break
    if idx is None:
        # Match by filename only (path moved / case)
        for i, p in enumerate(pool):
            if p.name.lower() == Path(current).name.lower():
                idx = i
                break
    if idx is None:
        return pool[0] if step >= 0 else pool[-1]

    return pool[(idx + step) % len(pool)]


def resolve_file_arg(
    raw: str | Path,
    *,
    base: Path | None = None,
    extensions: frozenset[str] | None = None,
) -> Path:
    """Resolve --file path; raise FileNotFoundError / ValueError if unusable."""
    p = Path(raw).expanduser()
    if not p.is_absolute() and base is not None:
        candidate = (base / p).resolve()
        if candidate.is_file():
            p = candidate
        else:
            p = p.resolve() if p.exists() else candidate
    else:
        p = p.resolve()

    if not p.is_file():
        raise FileNotFoundError(f"Image not found: {raw}")
    if extensions is not None and p.suffix.lower() not in extensions:
        raise ValueError(
            f"Unsupported image type {p.suffix!r} (allowed: {sorted(extensions)})"
        )
    return p


def select_wallpaper(
    grok_daily: Path,
    curated: Path,
    day: date,
    extensions: frozenset[str],
    prefer_primary: bool = True,
) -> Path | None:
    """Pick the best wallpaper for *day*.

    Strategy
    --------
    1. Primary (Grok_Daily): file with today's date in the name, else newest.
    2. If primary empty → secondary (Curated): same date logic, else newest.
    3. If prefer_primary is False, try Curated first (rare; for testing).
    """
    primary = (grok_daily, "Grok_Daily")
    secondary = (curated, "Curated")
    order = [primary, secondary] if prefer_primary else [secondary, primary]

    for folder, label in order:
        images = list_images(folder, extensions)
        log.debug("%s: %d image(s) in %s", label, len(images), folder)
        if not images:
            continue
        chosen = prefer_date_match(images, day)
        if chosen is not None:
            log.info("Selected from %s: %s", label, chosen)
            return chosen

    log.error(
        "No wallpapers found in primary (%s) or secondary (%s)",
        grok_daily,
        curated,
    )
    return None
