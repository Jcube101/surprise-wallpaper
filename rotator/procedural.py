"""Offline tasteful fallback: soft abstract 16:9 PNG (stdlib only).

Used when XAI_API_KEY is not configured so `wallpaper.py new` still
produces a real, settable file. Clearly secondary to Grok Imagine / xAI.
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(
        ">I", zlib.crc32(tag + data) & 0xFFFFFFFF
    )


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def write_soft_abstract_png(
    dest: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    seed: int = 0,
    palette: str = "mist",
) -> Path:
    """Write a calm gradient + soft orb wallpaper to *dest* as PNG."""
    palettes = {
        "mist": ((230, 228, 240), (200, 210, 220), (180, 190, 210), (255, 250, 245)),
        "sage": ((220, 230, 215), (190, 205, 185), (170, 185, 175), (250, 248, 240)),
        "indigo": ((25, 30, 55), (45, 40, 70), (90, 60, 80), (200, 180, 190)),
        "pearl": ((240, 242, 245), (220, 225, 235), (200, 210, 225), (255, 252, 248)),
    }
    c0, c1, c2, highlight = palettes.get(palette, palettes["mist"])

    # Deterministic soft variation from seed
    ox = (seed % 97) / 97.0
    oy = ((seed // 97) % 89) / 89.0

    rows: list[bytes] = []
    for y in range(height):
        fy = y / max(height - 1, 1)
        row = bytearray()
        row.append(0)  # filter none
        for x in range(width):
            fx = x / max(width - 1, 1)
            # Vertical sky→ground wash
            t = fy
            r = _lerp(c0[0], c1[0], t)
            g = _lerp(c0[1], c1[1], t)
            b = _lerp(c0[2], c1[2], t)
            # Diagonal second wash
            d = (fx + fy) * 0.5
            r = _lerp(r, c2[0], d * 0.35)
            g = _lerp(g, c2[1], d * 0.35)
            b = _lerp(b, c2[2], d * 0.35)
            # Soft orb (sun / moon)
            cx, cy = 0.72 + ox * 0.08, 0.28 + oy * 0.08
            dist = math.hypot(fx - cx, (fy - cy) * (width / height))
            glow = max(0.0, 1.0 - dist / 0.22) ** 2
            r = min(255, r + (highlight[0] - r) * glow * 0.55)
            g = min(255, g + (highlight[1] - g) * glow * 0.55)
            b = min(255, b + (highlight[2] - b) * glow * 0.55)
            # Gentle vignette
            vx = (fx - 0.5) * 2
            vy = (fy - 0.5) * 2
            vig = 1.0 - 0.12 * (vx * vx + vy * vy)
            r = max(0, min(255, int(r * vig)))
            g = max(0, min(255, int(g * vig)))
            b = max(0, min(255, int(b * vig)))
            row.extend((r, g, b))
        rows.append(bytes(row))

    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(png)
    return dest
