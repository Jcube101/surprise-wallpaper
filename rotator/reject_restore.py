"""Reject today's image (NASA fallback) and restore past images."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from rotator.apod import fetch_apod
from rotator.config import Config, PROJECT_ROOT
from rotator.core import apply_image
from rotator.journal import (
    JournalEntry,
    append_entry,
    find_entry_file,
)
from rotator.state import today_in_tz

log = logging.getLogger(__name__)


def rejected_dir(cfg: Config) -> Path:
    d = cfg.grok_daily_dir / "_rejected"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reject_today(cfg: Config, *, project_root: Path | None = None) -> tuple[bool, str]:
    """Move today's wallpaper to _rejected/, fetch APOD, set it, journal."""
    root = Path(project_root or PROJECT_ROOT)
    day = today_in_tz(cfg.timezone)
    day_str = day.isoformat()

    rel = find_entry_file(root, day_str)
    moved_to = None
    if rel:
        src = Path(rel)
        if not src.is_file():
            # try under grok_daily by name
            cand = cfg.grok_daily_dir / Path(rel).name
            if cand.is_file():
                src = cand
        if src.is_file() and "_rejected" not in src.parts:
            dest = rejected_dir(cfg) / src.name
            if dest.exists():
                dest = rejected_dir(cfg) / f"{src.stem}_rej{src.suffix}"
            shutil.move(str(src), str(dest))
            moved_to = dest
            log.info("Moved rejected image → %s", dest)
            append_entry(
                root,
                JournalEntry(
                    day=day_str,
                    theme="reject",
                    title=f"Rejected {src.name}",
                    description=f"User rejected today's image; moved to {dest.name}",
                    filename=str(dest),
                    source="reject",
                    detail="awaiting NASA replacement",
                    status="rejected",
                ),
            )

    paths = fetch_apod(
        api_key=cfg.nasa_api_key,
        count=1,
        dest_dir=cfg.apod_save_to or cfg.curated_dir,
    )
    if not paths:
        return False, "Reject: moved local file (if any) but NASA APOD download failed."

    nasa_path = paths[0]
    result = apply_image(cfg, nasa_path)
    append_entry(
        root,
        JournalEntry(
            day=day_str,
            theme="nasa",
            title=f"NASA APOD · {nasa_path.name}",
            description=(
                "Replacement wallpaper from NASA Astronomy Picture of the Day "
                "after user rejected today's generated image."
            ),
            filename=str(nasa_path),
            source="nasa-apod",
            detail=f"replaced={moved_to.name if moved_to else 'none'}",
            status="active",
        ),
    )
    if not result.success:
        return False, f"APOD saved but set failed: {result.message}"
    msg = f"Rejected today's image. NASA set: {nasa_path.name}"
    if moved_to:
        msg += f" (archived {moved_to.name})"
    return True, msg


def restore_image(
    cfg: Config,
    *,
    path: Path | None = None,
    day: str | None = None,
    project_root: Path | None = None,
) -> tuple[bool, str]:
    """Bring back a past image (from Grok_Daily, Curated, or _rejected) and set it."""
    root = Path(project_root or PROJECT_ROOT)
    day_str = day or today_in_tz(cfg.timezone).isoformat()

    image: Path | None = path
    if image is None and day:
        rel = find_entry_file(root, day)
        if rel:
            image = Path(rel)
            if not image.is_file():
                # search rejected + grok_daily by basename
                name = Path(rel).name
                for folder in (
                    cfg.grok_daily_dir,
                    rejected_dir(cfg),
                    cfg.curated_dir,
                ):
                    cand = folder / name
                    if cand.is_file():
                        image = cand
                        break

    if image is None or not image.is_file():
        return False, "Could not find image to restore. Pass --file or --date with a known entry."

    image = Path(image).resolve()
    # If in _rejected, copy back to Grok_Daily
    if "_rejected" in image.parts:
        dest = cfg.grok_daily_dir / image.name
        shutil.copy2(image, dest)
        image = dest
        log.info("Restored from _rejected → %s", dest)

    result = apply_image(cfg, image)
    append_entry(
        root,
        JournalEntry(
            day=day_str,
            theme="restore",
            title=f"Restored {image.name}",
            description=f"User restored previous wallpaper: {image.name}",
            filename=str(image),
            source="restore",
            detail=f"requested_day={day or 'today'}",
            status="restored",
        ),
    )
    if not result.success:
        return False, result.message
    return True, f"Restored and set: {image.name}"


def list_restorable(cfg: Config, limit: int = 30) -> list[str]:
    """Paths worth restoring: Grok_Daily + _rejected (newest first)."""
    files: list[Path] = []
    for folder in (cfg.grok_daily_dir, rejected_dir(cfg), cfg.curated_dir):
        if not folder.is_dir():
            continue
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".bmp",
            }:
                files.append(p)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(p) for p in files[:limit]]
