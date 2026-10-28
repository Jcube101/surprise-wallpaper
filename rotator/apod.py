"""Optional NASA Astronomy Picture of the Day (APOD) downloader for Curated/."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

APOD_URL = "https://api.nasa.gov/planetary/apod"
USER_AGENT = "GrokSurpriseWallpaperRotator/1.0 (local; +https://api.nasa.gov)"
_SAFE_NAME = re.compile(r"[^\w.\-]+", re.UNICODE)


def _http_get_json(url: str, timeout: float = 30.0) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def _http_download(url: str, dest: Path, timeout: float = 60.0) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())


def _slug(text: str, max_len: int = 60) -> str:
    s = _SAFE_NAME.sub("_", text.strip()).strip("_")
    return (s[:max_len] or "apod").rstrip("._")


def fetch_apod(
    api_key: str = "DEMO_KEY",
    count: int = 1,
    dest_dir: Path | None = None,
    on_date: date | None = None,
) -> list[Path]:
    """Download APOD image(s) into *dest_dir*.

    Uses the public NASA APOD API. ``DEMO_KEY`` works with low rate limits;
    get a free key at https://api.nasa.gov/

    Only image media types are saved (videos are skipped with a log note).

    Returns
    -------
    list[Path]
        Paths of newly downloaded files (empty if offline / all skipped).
    """
    if dest_dir is None:
        raise ValueError("dest_dir is required")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    params: dict[str, str] = {"api_key": api_key or "DEMO_KEY"}
    if on_date is not None:
        params["date"] = on_date.isoformat()
    elif count > 1:
        # Random recent images (API supports count=1..100)
        params["count"] = str(min(count, 100))

    query = urllib.parse.urlencode(params)
    url = f"{APOD_URL}?{query}"
    log.info("Requesting APOD: %s", url.replace(api_key, "***") if api_key else url)

    try:
        payload = _http_get_json(url)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        log.error("APOD HTTP %s: %s", e.code, body)
        return []
    except urllib.error.URLError as e:
        log.error("APOD offline / network error: %s", e.reason)
        return []
    except TimeoutError:
        log.error("APOD request timed out")
        return []
    except json.JSONDecodeError as e:
        log.error("APOD invalid JSON: %s", e)
        return []

    items = payload if isinstance(payload, list) else [payload]
    saved: list[Path] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        media = item.get("media_type", "image")
        if media != "image":
            log.info(
                "Skipping non-image APOD (%s): %s",
                media,
                item.get("title", "?"),
            )
            continue

        # Prefer HD when available
        img_url = item.get("hdurl") or item.get("url")
        if not img_url:
            log.warning("APOD entry has no image URL: %s", item.get("title"))
            continue

        day = item.get("date") or date.today().isoformat()
        title = item.get("title") or "apod"
        ext = Path(urllib.parse.urlparse(img_url).path).suffix.lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            ext = ".jpg"

        filename = f"APOD_{day}_{_slug(title)}{ext}"
        dest = dest_dir / filename

        if dest.is_file():
            log.info("Already have %s; skipping download", dest.name)
            saved.append(dest)
            continue

        try:
            log.info("Downloading %s → %s", img_url, dest.name)
            _http_download(img_url, dest)
            saved.append(dest)
            log.info("Saved APOD: %s", dest)
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            log.error("Failed to download %s: %s", img_url, e)
            if dest.is_file():
                try:
                    dest.unlink()
                except OSError:
                    pass

    return saved
