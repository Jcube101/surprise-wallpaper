"""Create a daily tasteful surprise file in Grok_Daily/."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from rotator.procedural import write_soft_abstract_png
from rotator.state import today_in_tz
from rotator.tasteful import (
    TASTEFUL_THEMES,
    build_prompt,
    pick_theme,
    recent_slugs_from_names,
)
from rotator.xai_image import resolve_xai_api_key, save_generated

log = logging.getLogger(__name__)

_PALETTE_FOR_SLUG = {
    "misty_lake_dawn": "mist",
    "sage_hills_gold": "sage",
    "indigo_crescent": "indigo",
    "paper_clouds": "pearl",
    "moonlit_grove": "mist",
    "desert_quiet_stars": "sage",
    "coastal_haze": "pearl",
    "lavender_fields_dusk": "mist",
    "frozen_fjord_light": "pearl",
    "ink_mountain_void": "mist",
    "tea_garden_fog": "sage",
    "pearl_horizon": "pearl",
}


def create_surprise(
    grok_daily: Path,
    *,
    timezone: str = "Asia/Kolkata",
    slug: str | None = None,
    prefer_xai: bool = True,
    force_procedural: bool = False,
) -> tuple[Path, str, str]:
    """Create one tasteful wallpaper in *grok_daily*.

    Returns (path, source, prompt) where source is ``xai`` or ``procedural``.
    """
    grok_daily = Path(grok_daily)
    grok_daily.mkdir(parents=True, exist_ok=True)
    day = today_in_tz(timezone)

    existing = [p.name for p in grok_daily.iterdir() if p.is_file()] if grok_daily.is_dir() else []
    avoid = recent_slugs_from_names(existing)
    theme = pick_theme(slug=slug, avoid_slugs=avoid)
    prompt = build_prompt(theme)

    # Unique path for today
    base = f"{day.isoformat()}_{theme.slug}"
    dest_png = grok_daily / f"{base}.png"
    dest_jpg = grok_daily / f"{base}.jpg"
    if dest_png.exists() or dest_jpg.exists():
        n = 2
        while True:
            dest_png = grok_daily / f"{base}_{n:02d}.png"
            dest_jpg = grok_daily / f"{base}_{n:02d}.jpg"
            if not dest_png.exists() and not dest_jpg.exists():
                break
            n += 1

    use_xai = prefer_xai and not force_procedural and resolve_xai_api_key()
    if use_xai:
        try:
            # Prefer png path; API may return jpeg bytes — still fine as .png only if PNG
            path = save_generated(prompt, dest_jpg)
            # Detect JPEG magic and keep .jpg; if PNG magic rename
            head = path.read_bytes()[:8]
            if head.startswith(b"\x89PNG"):
                final = dest_png
                if path != final:
                    path.replace(final)
                path = final
            log.info("Surprise via xAI: %s", path.name)
            return path, "xai", prompt
        except Exception as e:
            log.warning("xAI generation failed (%s); using procedural fallback", e)

    palette = _PALETTE_FOR_SLUG.get(theme.slug, "mist")
    # seed from slug hash for variety
    seed = sum(ord(c) for c in theme.slug) + day.toordinal()
    path = write_soft_abstract_png(dest_png, seed=seed, palette=palette)
    log.info("Surprise via procedural fallback: %s", path.name)
    return path, "procedural", prompt


def list_tasteful_slugs() -> list[str]:
    return [t.slug for t in TASTEFUL_THEMES]
