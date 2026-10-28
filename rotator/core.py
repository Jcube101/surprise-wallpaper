"""Core daily wallpaper flow: select → set → record state → notify."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from rotator.config import Config, ensure_directories
from rotator.notify import show_toast
from rotator.selector import select_wallpaper
from rotator.state import already_set_today, today_in_tz, write_last_set
from rotator.windows_wallpaper import dismiss_blocking_input_overlay, set_wallpaper

log = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Outcome of a rotator run."""

    success: bool
    skipped: bool
    message: str
    image_path: Path | None = None
    day: str | None = None


def apply_image(
    cfg: Config,
    image: Path,
    *,
    dry_run: bool = False,
) -> RunResult:
    """Force-set a specific image and update state (always force)."""
    ensure_directories(cfg)
    day = today_in_tz(cfg.timezone)
    day_str = day.isoformat()
    image = Path(image)

    if dry_run:
        msg = f"[dry-run] Would set wallpaper for {day_str}: {image}"
        log.info(msg)
        return RunResult(
            success=True,
            skipped=False,
            message=msg,
            image_path=image,
            day=day_str,
        )

    try:
        set_wallpaper(image)
    except (OSError, FileNotFoundError) as e:
        msg = f"Failed to set wallpaper: {e}"
        log.error(msg)
        return RunResult(
            success=False,
            skipped=False,
            message=msg,
            image_path=image,
            day=day_str,
        )

    write_last_set(cfg.state_file, day, image)

    toast_body = f"{day_str}\n{image.name}"
    if cfg.show_toast:
        show_toast(cfg.toast_title, toast_body, image_path=image)

    msg = f"Wallpaper set for {day_str}: {image.name}"
    log.info(msg)
    return RunResult(
        success=True,
        skipped=False,
        message=msg,
        image_path=image,
        day=day_str,
    )


def run_daily(
    cfg: Config,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> RunResult:
    """Select and set today's wallpaper.

    Parameters
    ----------
    force:
        Ignore .last_set.txt and set again even if already done today.
    dry_run:
        Resolve selection and log it, but do not change wallpaper or state.
    """
    ensure_directories(cfg)
    day = today_in_tz(cfg.timezone)
    day_str = day.isoformat()

    if not force and already_set_today(cfg.state_file, cfg.timezone):
        # Logon/unlock hits this path and does not set a wallpaper. A leftover
        # fullscreen Input Experience window still has to be cleared or the
        # desktop stays blank with no icons and no right-click menu.
        if not dry_run:
            hidden = dismiss_blocking_input_overlay()
            if hidden:
                log.info(
                    "Hid %s fullscreen Windows Input Experience window(s) covering the desktop",
                    hidden,
                )
        msg = f"Already set for {day_str} (see {cfg.state_file.name}); skipping"
        log.info(msg)
        return RunResult(success=True, skipped=True, message=msg, day=day_str)

    image = select_wallpaper(
        grok_daily=cfg.grok_daily_dir,
        curated=cfg.curated_dir,
        day=day,
        extensions=cfg.image_extensions,
        prefer_primary=cfg.prefer_primary,
    )

    if image is None:
        msg = (
            "No wallpapers available offline. "
            f"Add images to {cfg.grok_daily_dir} or {cfg.curated_dir}."
        )
        log.error(msg)
        return RunResult(success=False, skipped=False, message=msg, day=day_str)

    return apply_image(cfg, image, dry_run=dry_run)
