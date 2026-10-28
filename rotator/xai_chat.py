"""xAI chat completions (Grok) with usage → cost logging."""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

from rotator.costs import (
    CostEvent,
    estimate_chat_usd,
    record_cost,
    utc_now_iso,
)
from rotator.xai_image import resolve_xai_api_key

log = logging.getLogger(__name__)

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_CHAT_MODEL = "grok-4-1-fast-reasoning"
USER_AGENT = "GrokSurpriseWallpaperRotator/2.0"


def resolve_chat_model() -> str:
    return (
        (os.environ.get("XAI_CHAT_MODEL") or "").strip()
        or DEFAULT_CHAT_MODEL
    )


def chat_completion(
    messages: list[dict[str, str]],
    *,
    project_root,
    day_ist: str,
    note: str = "",
    model: str | None = None,
    temperature: float = 0.7,
    timeout: float = 120.0,
) -> tuple[str, CostEvent]:
    """Return (assistant_text, cost_event). Raises RuntimeError on failure."""
    key = resolve_xai_api_key()
    if not key:
        raise RuntimeError("XAI_API_KEY required for Grok chat research")

    model = model or resolve_chat_model()
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        XAI_CHAT_URL,
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
        detail = e.read().decode("utf-8", errors="replace")[:600]
        raise RuntimeError(f"xAI chat HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"xAI chat network error: {e.reason}") from e

    text = _extract_text(payload)
    usage = payload.get("usage") or {}
    pin = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    pout = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    # Some APIs only return total_tokens
    if pin == 0 and pout == 0 and usage.get("total_tokens"):
        pout = int(usage["total_tokens"])

    event = CostEvent(
        ts_utc=utc_now_iso(),
        day_ist=day_ist,
        kind="chat",
        model=model,
        prompt_tokens=pin,
        completion_tokens=pout,
        image_count=0,
        est_usd=estimate_chat_usd(pin, pout),
        note=note,
        ok=True,
    )
    record_cost(project_root, event)
    return text, event


def chat_json(
    system: str,
    user: str,
    *,
    project_root,
    day_ist: str,
    note: str = "",
    model: str | None = None,
    temperature: float = 0.5,
) -> tuple[dict[str, Any], CostEvent]:
    """Ask for JSON only; parse object from response."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    text, event = chat_completion(
        messages,
        project_root=project_root,
        day_ist=day_ist,
        note=note,
        model=model,
        temperature=temperature,
    )
    return _parse_json_object(text), event


def _extract_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError(f"No choices in chat response: {list(payload.keys())}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for p in content:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(p.get("text") or "")
            elif isinstance(p, str):
                parts.append(p)
        return "\n".join(parts)
    raise RuntimeError("Unexpected message content shape")


def _parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    # strip markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    # find first { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        obj = json.loads(text[start : end + 1])
        if isinstance(obj, dict):
            return obj
    raise RuntimeError(f"Could not parse JSON from model: {text[:400]}")
