"""Track estimated xAI API spend (chat + images) to logs/."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# Rough defaults (USD). Override via env without code changes.
# Update when xAI pricing changes: https://docs.x.ai/
_DEFAULT_CHAT_IN_PER_M = 3.0
_DEFAULT_CHAT_OUT_PER_M = 15.0
_DEFAULT_IMAGE_PER = 0.07


def _fenv(name: str, default: float) -> float:
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class CostEvent:
    ts_utc: str
    day_ist: str
    kind: str  # chat | image
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    image_count: int = 0
    est_usd: float = 0.0
    note: str = ""
    ok: bool = True


def estimate_chat_usd(prompt_tokens: int, completion_tokens: int) -> float:
    pin = _fenv("XAI_PRICE_CHAT_INPUT_PER_MTOK", _DEFAULT_CHAT_IN_PER_M)
    pout = _fenv("XAI_PRICE_CHAT_OUTPUT_PER_MTOK", _DEFAULT_CHAT_OUT_PER_M)
    return (prompt_tokens / 1_000_000.0) * pin + (completion_tokens / 1_000_000.0) * pout


def estimate_image_usd(n: int = 1) -> float:
    per = _fenv("XAI_PRICE_IMAGE_USD", _DEFAULT_IMAGE_PER)
    return per * max(0, n)


def costs_jsonl_path(project_root: Path) -> Path:
    return project_root / "logs" / "xai_costs.jsonl"


def costs_md_path(project_root: Path) -> Path:
    return project_root / "logs" / "xai_costs.md"


def record_cost(project_root: Path, event: CostEvent) -> None:
    """Append JSONL row and refresh markdown summary."""
    project_root = Path(project_root)
    jsonl = costs_jsonl_path(project_root)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    with jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
    log.info(
        "Cost %s %s model=%s est=$%.4f note=%s",
        event.kind,
        event.day_ist,
        event.model,
        event.est_usd,
        event.note[:80],
    )
    _rewrite_md(project_root)


def _rewrite_md(project_root: Path) -> None:
    jsonl = costs_jsonl_path(project_root)
    md = costs_md_path(project_root)
    rows: list[CostEvent] = []
    if jsonl.is_file():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                rows.append(CostEvent(**{k: d[k] for k in CostEvent.__dataclass_fields__ if k in d}))
            except (json.JSONDecodeError, TypeError, KeyError):
                continue

    total = sum(r.est_usd for r in rows)
    by_day: dict[str, float] = {}
    for r in rows:
        by_day[r.day_ist] = by_day.get(r.day_ist, 0.0) + r.est_usd

    lines = [
        "# xAI API cost log (estimated)",
        "",
        "Estimates use env rates (defaults are approximate — set `XAI_PRICE_*` to match your plan):",
        "",
        f"- Chat input: `${_fenv('XAI_PRICE_CHAT_INPUT_PER_MTOK', _DEFAULT_CHAT_IN_PER_M)}` / MTok",
        f"- Chat output: `${_fenv('XAI_PRICE_CHAT_OUTPUT_PER_MTOK', _DEFAULT_CHAT_OUT_PER_M)}` / MTok",
        f"- Image: `${_fenv('XAI_PRICE_IMAGE_USD', _DEFAULT_IMAGE_PER)}` / image",
        "",
        f"**Lifetime estimated spend: ${total:.4f} USD** ({len(rows)} events)",
        "",
        "## By day (IST)",
        "",
        "| Day | Est. USD |",
        "|-----|----------|",
    ]
    for day in sorted(by_day.keys(), reverse=True)[:60]:
        lines.append(f"| {day} | ${by_day[day]:.4f} |")

    lines += [
        "",
        "## Recent events",
        "",
        "| UTC | Day IST | Kind | Model | Tok in/out | Images | Est. USD | Note |",
        "|-----|---------|------|-------|------------|--------|----------|------|",
    ]
    for r in reversed(rows[-40:]):
        note = (r.note or "").replace("|", "/")[:60]
        lines.append(
            f"| {r.ts_utc[:19]} | {r.day_ist} | {r.kind} | `{r.model}` | "
            f"{r.prompt_tokens}/{r.completion_tokens} | {r.image_count} | "
            f"${r.est_usd:.4f} | {note} |"
        )
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def total_spend(project_root: Path) -> float:
    jsonl = costs_jsonl_path(project_root)
    if not jsonl.is_file():
        return 0.0
    total = 0.0
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        try:
            total += float(json.loads(line).get("est_usd") or 0)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return total
