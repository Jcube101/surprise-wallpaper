"""Optional xAI Grok Imagine image generation (stdlib HTTP).

Requires XAI_API_KEY in the environment or .env.
Endpoint: POST https://api.x.ai/v1/images/generations
Model default: grok-imagine-image (or grok-imagine-image-quality).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

XAI_IMAGES_URL = "https://api.x.ai/v1/images/generations"
DEFAULT_MODEL = "grok-imagine-image"
USER_AGENT = "GrokSurpriseWallpaperRotator/2.0"


def resolve_xai_api_key() -> str | None:
    for key in ("XAI_API_KEY", "GROK_API_KEY"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    return None


def resolve_image_model() -> str:
    return (
        (os.environ.get("XAI_IMAGE_MODEL") or "").strip()
        or DEFAULT_MODEL
    )


def generate_image_bytes(
    prompt: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float = 120.0,
    project_root: Path | None = None,
    day_ist: str | None = None,
    note: str = "image",
) -> bytes:
    """Call xAI images API; return raw image bytes (PNG/JPEG).

    When *project_root* and *day_ist* are set, records estimated cost.
    """
    key = api_key or resolve_xai_api_key()
    if not key:
        raise RuntimeError(
            "No XAI_API_KEY (or GROK_API_KEY). Add it to .env to generate via API."
        )

    model = model or resolve_image_model()
    body = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "aspect_ratio": "16:9",
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        XAI_IMAGES_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"xAI images HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"xAI images network error: {e.reason}") from e

    if project_root is not None and day_ist is not None:
        from rotator.costs import (
            CostEvent,
            estimate_image_usd,
            record_cost,
            utc_now_iso,
        )

        record_cost(
            project_root,
            CostEvent(
                ts_utc=utc_now_iso(),
                day_ist=day_ist,
                kind="image",
                model=model,
                prompt_tokens=0,
                completion_tokens=0,
                image_count=1,
                est_usd=estimate_image_usd(1),
                note=note,
                ok=True,
            ),
        )

    return _extract_image_bytes(payload)


def _extract_image_bytes(payload: dict) -> bytes:
    """Support URL or b64_json response shapes."""
    data = payload.get("data") or payload.get("images") or []
    if not data and isinstance(payload.get("url"), str):
        return _download(payload["url"])

    if not data:
        raise RuntimeError(f"Unexpected xAI response keys: {list(payload.keys())}")

    item = data[0] if isinstance(data, list) else data
    if not isinstance(item, dict):
        raise RuntimeError("Unexpected xAI image item type")

    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])

    url = item.get("url") or item.get("image_url")
    if isinstance(url, dict):
        url = url.get("url")
    if url:
        return _download(str(url))

    raise RuntimeError(f"No image url/b64 in response item: {list(item.keys())}")


def _download(url: str, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def save_generated(
    prompt: str,
    dest: Path,
    *,
    api_key: str | None = None,
    model: str | None = None,
    project_root: Path | None = None,
    day_ist: str | None = None,
    note: str = "image",
) -> Path:
    """Generate and write *dest*. Extension should match content (.png/.jpg)."""
    raw = generate_image_bytes(
        prompt,
        api_key=api_key,
        model=model,
        project_root=project_root,
        day_ist=day_ist,
        note=note,
    )
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    # Fix extension from magic
    if raw[:8].startswith(b"\x89PNG") and dest.suffix.lower() != ".png":
        dest = dest.with_suffix(".png")
        dest.write_bytes(raw)
    elif raw[:2] == b"\xff\xd8" and dest.suffix.lower() not in {".jpg", ".jpeg"}:
        dest = dest.with_suffix(".jpg")
        dest.write_bytes(raw)
    log.info("Saved xAI image → %s (%d bytes)", dest, len(raw))
    return dest
