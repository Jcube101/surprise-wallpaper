"""Tasteful surprise prompts — elegant, serene, subtle fantastical.

Avoid tryhard steampunk, maximalist drama, neon cyberpunk, and busy
creature-filled scenes. Prefer negative space, soft palettes, quiet mood.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

# Shared style suffix for every generation
STYLE_SUFFIX = (
    "16:9 desktop wallpaper, elegant and serene, subtle fantastical mood, "
    "sophisticated artistic painting, soft light, refined composition with "
    "negative space, no text, no logos, no watermarks, no people, "
    "avoid steampunk, avoid neon cyberpunk, avoid overly dramatic contrast"
)


@dataclass(frozen=True)
class TastefulTheme:
    slug: str
    title: str
    prompt: str


TASTEFUL_THEMES: tuple[TastefulTheme, ...] = (
    TastefulTheme(
        slug="misty_lake_dawn",
        title="Misty lake at dawn",
        prompt=(
            "Soft misty lake at dawn, pale lavender and champagne sky, "
            "distant mountains as delicate ink-wash silhouettes, quiet "
            "reflective water, Japanese-inspired painterly calm"
        ),
    ),
    TastefulTheme(
        slug="sage_hills_gold",
        title="Sage hills with gold ribbon",
        prompt=(
            "Soft rolling hills in pale sage and cream under a pearl-grey sky, "
            "a single thin ribbon of gold light on the horizon, impressionist "
            "brushwork, gallery-quiet atmosphere"
        ),
    ),
    TastefulTheme(
        slug="indigo_crescent",
        title="Indigo crescent quietude",
        prompt=(
            "Deep indigo night fading to dusty rose at the horizon, delicate "
            "crescent moon and sparse stars, soft cloud veils, oil-painting "
            "texture, luxurious serenity"
        ),
    ),
    TastefulTheme(
        slug="paper_clouds",
        title="Paper-soft clouds",
        prompt=(
            "Endless soft layered clouds in ivory and blush pink, gentle "
            "diffused sunlight, airy minimal composition, dreamy but restrained "
            "pastel painting"
        ),
    ),
    TastefulTheme(
        slug="moonlit_grove",
        title="Moonlit quiet grove",
        prompt=(
            "Sparse moonlit birch grove in cool silver-blue, soft fog between "
            "trunks, single path of pale light, contemplative Nordic fantasy "
            "mood without creatures"
        ),
    ),
    TastefulTheme(
        slug="desert_quiet_stars",
        title="Desert under quiet stars",
        prompt=(
            "Vast quiet desert dunes in muted terracotta and sand, clear sky "
            "with sparse stars, long soft shadows, meditative wide landscape, "
            "subtle magical stillness"
        ),
    ),
    TastefulTheme(
        slug="coastal_haze",
        title="Coastal morning haze",
        prompt=(
            "Coastal cliffs dissolving into morning haze, sea and sky nearly "
            "the same pale aqua-grey, tiny white bird shapes far away, "
            "Turner-like soft atmosphere, elegant restraint"
        ),
    ),
    TastefulTheme(
        slug="lavender_fields_dusk",
        title="Lavender fields at dusk",
        prompt=(
            "Gentle rows of lavender fading into violet dusk, soft gradient "
            "sky peach to lilac, no buildings, peaceful European countryside "
            "as painterly abstraction"
        ),
    ),
    TastefulTheme(
        slug="frozen_fjord_light",
        title="Frozen fjord light",
        prompt=(
            "Still frozen fjord reflecting a pale mint and rose aurora, "
            "minimal snow ridges, quiet Nordic sublime, soft glow not "
            "theatrical lightning"
        ),
    ),
    TastefulTheme(
        slug="ink_mountain_void",
        title="Ink mountain void",
        prompt=(
            "Single mountain form in sumi-e ink wash on vast empty parchment "
            "sky, one pale sun disc, extreme negative space, museum-calm "
            "Asian landscape sensibility"
        ),
    ),
    TastefulTheme(
        slug="tea_garden_fog",
        title="Tea garden fog",
        prompt=(
            "Terraced tea hills in soft fog, muted greens and greys, thin "
            "wooden bridge barely visible, peaceful contemplative painting, "
            "subtle otherworldly softness"
        ),
    ),
    TastefulTheme(
        slug="pearl_horizon",
        title="Pearl horizon",
        prompt=(
            "Abstract sea meeting sky in pearlescent gradients of silver, "
            "champagne, and cool blue, horizon almost lost, minimal and "
            "luxurious, soft fantasy abstraction"
        ),
    ),
)


_SLUG_RE = re.compile(r"[^a-z0-9_]+")


def build_prompt(theme: TastefulTheme) -> str:
    """Full generation prompt for Grok Imagine / xAI images API."""
    return f"{theme.prompt}. {STYLE_SUFFIX}."


def pick_theme(
    *,
    slug: str | None = None,
    avoid_slugs: set[str] | None = None,
    rng: random.Random | None = None,
) -> TastefulTheme:
    """Pick a theme by slug or at random, preferring unused slugs."""
    rng = rng or random.Random()
    avoid = avoid_slugs or set()

    if slug:
        for t in TASTEFUL_THEMES:
            if t.slug == slug:
                return t
        # Allow free-form slug with a generic prompt shell
        clean = _SLUG_RE.sub("_", slug.lower()).strip("_") or "tasteful_surprise"
        return TastefulTheme(
            slug=clean,
            title=clean.replace("_", " "),
            prompt=(
                f"Elegant serene {clean.replace('_', ' ')} landscape, "
                "soft refined palette, subtle fantastical atmosphere, "
                "sophisticated artistic painting"
            ),
        )

    pool = [t for t in TASTEFUL_THEMES if t.slug not in avoid]
    if not pool:
        pool = list(TASTEFUL_THEMES)
    return rng.choice(pool)


def recent_slugs_from_names(filenames: list[str]) -> set[str]:
    """Extract theme slugs from names like 2026-07-15_misty_lake_dawn.jpg."""
    found: set[str] = set()
    for name in filenames:
        stem = name.rsplit(".", 1)[0]
        m = re.match(r"\d{4}-\d{2}-\d{2}_(.+)", stem)
        if m:
            slug = m.group(1).lower()
            # drop trailing _02 uniqueness suffixes
            slug = re.sub(r"_\d{2}$", "", slug)
            found.add(slug)
    return found
