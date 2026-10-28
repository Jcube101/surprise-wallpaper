"""Optional Pexels photo download for Curated/ (secondary source).

Free API key: https://www.pexels.com/api/
Env: PEXELS_API_KEY

Complements NASA APOD — real photography only (never primary Grok path).
Graceful offline: returns [] on any failure.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

PEXELS_SEARCH = "https://api.pexels.com/v1/search"
USER_AGENT = "GrokSurpriseWallpaperRotator/1.1"
_SAFE = re.compile(r"[^\w.\-]+", re.UNICODE)


def resolve_pexels_api_key(config_key: str | None = None) -> str | None:
    env = (os.environ.get("PEXELS_API_KEY") or "").strip()
    if env:
        return env
    cfg = (config_key or "").strip()
    return cfg or None


def fetch_pexels(
    api_key: str | None = None,
    *,
    query: str = "minimal landscape nature serene",
    count: int = 1,
    dest_dir: Path | None = None,
    orientation: str = "landscape",
) -> list[Path]:
    """Download up to *count* landscape photos into *dest_dir*."""
    key = resolve_pexels_api_key(api_key)
    if not key:
        log.error("PEXELS_API_KEY not set — get a free key at https://www.pexels.com/api/")
        return []
    if dest_dir is None:
        raise ValueError("dest_dir is required")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    params = urllib.parse.urlencode(
        {
            "query": query,
            "per_page": max(1, min(count, 15)),
            "orientation": orientation,
            "size": "large",
        }
    )
    url = f"{PEXELS_SEARCH}?{params}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": key,
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        log.error("Pexels HTTP %s: %s", e.code, body)
        return []
    except urllib.error.URLError as e:
        log.error("Pexels offline / network error: %s", e.reason)
        return []
    except json.JSONDecodeError as e:
        log.error("Pexels invalid JSON: %s", e)
        return []

    photos = payload.get("photos") or []
    saved: list[Path] = []
    for photo in photos[:count]:
        src = (photo.get("src") or {})
        img_url = src.get("original") or src.get("large2x") or src.get("large")
        if not img_url:
            continue
        pid = photo.get("id", "x")
        alt = (photo.get("alt") or "pexels").strip()
        slug = _SAFE.sub("_", alt)[:40].strip("_") or "photo"
        ext = ".jpg"
        filename = f"Pexels_{pid}_{slug}{ext}"
        dest = dest_dir / filename
        if dest.is_file():
            log.info("Already have %s", dest.name)
            saved.append(dest)
            continue
        try:
            dreq = urllib.request.Request(img_url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(dreq, timeout=60) as resp:
                dest.write_bytes(resp.read())
            saved.append(dest)
            log.info("Saved Pexels: %s", dest)
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            log.error("Pexels download failed: %s", e)
            if dest.is_file():
                try:
                    dest.unlink()
                except OSError:
                    pass
    return saved
