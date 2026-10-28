"""Render a clean corporate 16:9 GTM channel infographic (Pillow).

Content is concentrated in the **center safe zone** so desktop icons on
the left/right (and top/bottom edges) stay usable.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

# Soft corporate palette
BG = (18, 24, 38)
PANEL = (28, 36, 54)
PANEL_EDGE = (22, 28, 42)
ACCENT = (56, 132, 255)
ACCENT2 = (72, 187, 168)
TEXT = (236, 240, 248)
MUTED = (148, 163, 184)
WHITE = (255, 255, 255)

# Edge margins as fraction of canvas — leave room for icons/taskbar
# Horizontal ~18% each side; vertical ~10% top / ~12% bottom
MARGIN_X_FRAC = 0.18
MARGIN_TOP_FRAC = 0.10
MARGIN_BOTTOM_FRAC = 0.12


def render_gtm_infographic(data: dict[str, Any], dest: Path) -> Path:
    """Write 1920×1080 PNG with content centered. Requires Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        raise RuntimeError(
            "Pillow is required for GTM infographics. Run: pip install pillow"
        ) from e

    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), BG)
    draw = ImageDraw.Draw(img)

    # Subtle vignette-ish edge panels (not content — just depth)
    edge_w = int(w * 0.06)
    draw.rectangle([0, 0, edge_w, h], fill=PANEL_EDGE)
    draw.rectangle([w - edge_w, 0, w, h], fill=PANEL_EDGE)

    font_title = _font(48)
    font_sub = _font(24)
    font_h = _font(22)
    font_body = _font(18)
    font_small = _font(15)

    company = str(data.get("company") or "Company")
    segment = data.get("segment")
    headline = str(data.get("headline") or "GTM channel map")
    narrative = str(data.get("narrative") or "")
    channels = data.get("channels") or []
    if not isinstance(channels, list):
        channels = []

    # Center content box
    mx = int(w * MARGIN_X_FRAC)
    my_top = int(h * MARGIN_TOP_FRAC)
    my_bot = int(h * MARGIN_BOTTOM_FRAC)
    box_x0, box_y0 = mx, my_top
    box_x1, box_y1 = w - mx, h - my_bot

    # Outer card for whole content (keeps bulk mid-screen)
    draw.rounded_rectangle(
        [box_x0, box_y0, box_x1, box_y1],
        radius=20,
        fill=PANEL,
        outline=ACCENT,
        width=2,
    )
    # Top accent stripe inside card
    draw.rounded_rectangle(
        [box_x0 + 2, box_y0 + 2, box_x1 - 2, box_y0 + 10],
        radius=4,
        fill=ACCENT,
    )

    pad = 36
    cx0 = box_x0 + pad
    cy0 = box_y0 + pad + 8
    inner_w = (box_x1 - box_x0) - 2 * pad

    title = company if not segment else f"{company} · {segment}"
    draw.text((cx0, cy0), title[:64], fill=WHITE, font=font_title)
    draw.text((cx0, cy0 + 56), headline[:80], fill=MUTED, font=font_sub)
    # No meta labels (e.g. "GTM · 16:9", disclaimers) — content only

    # Narrative inside center
    narr_y = cy0 + 100
    narr_h = 88
    draw.rounded_rectangle(
        [cx0, narr_y, box_x1 - pad, narr_y + narr_h],
        radius=12,
        fill=BG,
    )
    wrap_w = max(40, inner_w // 9)
    for i, line in enumerate(textwrap.wrap(narrative, width=wrap_w)[:3]):
        draw.text((cx0 + 16, narr_y + 14 + i * 24), line, fill=TEXT, font=font_body)

    # Channel cards — only inside remaining center area
    n = max(1, min(len(channels), 6))  # cap 6 so cards stay readable mid-screen
    channels = channels[:n]
    cols = 3 if n > 3 else max(1, n)
    rows = (n + cols - 1) // cols

    grid_top = narr_y + narr_h + 24
    grid_bottom = box_y1 - pad - 16  # use full card height; no footer meta
    gap = 16
    usable_w = inner_w
    usable_h = grid_bottom - grid_top
    card_w = (usable_w - gap * (cols - 1)) // cols
    card_h = max(80, (usable_h - gap * (rows - 1)) // rows)

    colors = [
        ACCENT,
        ACCENT2,
        (129, 140, 248),
        (251, 146, 60),
        (244, 114, 182),
        (52, 211, 153),
    ]

    # Char width estimate for wrapping inside cards
    char_w = max(22, card_w // 11)

    for i, ch in enumerate(channels):
        if not isinstance(ch, dict):
            continue
        r, c = divmod(i, cols)
        x0 = cx0 + c * (card_w + gap)
        y0 = grid_top + r * (card_h + gap)
        x1, y1 = x0 + card_w - 2, y0 + card_h - 2
        color = colors[i % len(colors)]
        draw.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=BG)
        draw.rectangle([x0, y0, x0 + 6, y1], fill=color)

        name = str(ch.get("name") or ch.get("channel") or f"Channel {i + 1}")
        role = str(ch.get("role") or ch.get("description") or "")
        tactics = ch.get("tactics") or ch.get("examples") or []
        if isinstance(tactics, str):
            tactics = [tactics]
        if not isinstance(tactics, list):
            tactics = []

        draw.text((x0 + 18, y0 + 12), name[:32].upper(), fill=color, font=font_h)
        y = y0 + 44
        for line in textwrap.wrap(role, width=char_w)[:3]:
            draw.text((x0 + 18, y), line, fill=TEXT, font=font_body)
            y += 22
        y += 6
        for t in tactics[:3]:
            bullet = f"• {str(t)[: max(20, char_w + 8)]}"
            draw.text((x0 + 18, y), bullet, fill=MUTED, font=font_small)
            y += 20
            if y > y1 - 24:
                break

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix.lower() != ".png":
        dest = dest.with_suffix(".png")
    img.save(dest, "PNG", optimize=True)
    return dest


def _font(size: int):
    from PIL import ImageFont

    candidates = [
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()
