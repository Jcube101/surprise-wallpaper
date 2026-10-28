"""Daily wallpaper journal — human-readable history of what appeared and why."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class JournalEntry:
    day: str
    theme: str
    title: str
    description: str
    filename: str
    source: str  # xai-image | gtm-code | nasa-apod | restore | procedural
    detail: str = ""
    est_cost_usd: float | None = None
    status: str = "active"  # active | rejected | restored


def journal_path(project_root: Path) -> Path:
    return project_root / "logs" / "wallpaper_journal.md"


def index_path(project_root: Path) -> Path:
    return project_root / "logs" / "wallpaper_index.md"


def append_entry(project_root: Path, entry: JournalEntry) -> None:
    project_root = Path(project_root)
    path = journal_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    cost = (
        f"${entry.est_cost_usd:.4f}"
        if entry.est_cost_usd is not None
        else "n/a"
    )
    block = (
        f"\n## {entry.day} · {entry.theme} · {entry.status}\n\n"
        f"- **File:** `{entry.filename}`\n"
        f"- **Title:** {entry.title}\n"
        f"- **Description:** {entry.description}\n"
        f"- **Source:** {entry.source}\n"
        f"- **Detail:** {entry.detail or '—'}\n"
        f"- **Est. xAI cost (this run):** {cost}\n"
    )
    if not path.is_file():
        header = (
            "# Wallpaper journal\n\n"
            "One entry per generation / reject / restore. "
            "Literary spoilers intentional. Dates use Asia/Kolkata.\n"
        )
        path.write_text(header + block, encoding="utf-8")
    else:
        with path.open("a", encoding="utf-8") as f:
            f.write(block)

    _refresh_index(project_root, entry)
    log.info("Journal: %s %s — %s", entry.day, entry.theme, entry.title)


def _refresh_index(project_root: Path, entry: JournalEntry) -> None:
    """Append one index line (simple scan file; full rebuild optional)."""
    idx = index_path(project_root)
    idx.parent.mkdir(parents=True, exist_ok=True)
    line = (
        f"| {entry.day} | {entry.theme} | {entry.status} | "
        f"{entry.title.replace('|', '/')} | `{Path(entry.filename).name}` |\n"
    )
    if not idx.is_file():
        idx.write_text(
            "# Wallpaper index\n\n"
            "| Day | Theme | Status | Title | File |\n"
            "|-----|-------|--------|-------|------|\n" + line,
            encoding="utf-8",
        )
    else:
        with idx.open("a", encoding="utf-8") as f:
            f.write(line)


_HEADING = re.compile(
    r"^## (?P<day>\d{4}-\d{2}-\d{2}) · (?P<theme>\w+) · (?P<status>\w+)\s*$",
    re.M,
)

# Creative themes that participate in the gtm → literary → painting cycle
CREATIVE_THEMES = frozenset({"gtm", "literary", "painting"})


def has_active_for_day(project_root: Path, day: str) -> bool:
    """True if journal has an active (non-rejected) entry for *day*."""
    path = journal_path(project_root)
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    matches = [
        m
        for m in _HEADING.finditer(text)
        if m.group("day") == day and m.group("status") in {"active", "restored"}
    ]
    return bool(matches)


def last_creative_theme_for_day(project_root: Path, day: str) -> str | None:
    """Most recent gtm/literary/painting theme generated for *day* (any status)."""
    path = journal_path(project_root)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    last: str | None = None
    for m in _HEADING.finditer(text):
        if m.group("day") != day:
            continue
        theme = m.group("theme")
        if theme in CREATIVE_THEMES:
            last = theme
    return last


def find_entry_file(project_root: Path, day: str) -> str | None:
    """Return filename field from latest entry for *day*, if any."""
    path = journal_path(project_root)
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?=^## )", text, flags=re.M)
    for block in reversed(parts):
        if not block.startswith(f"## {day}"):
            continue
        m = re.search(r"\*\*File:\*\*\s*`([^`]+)`", block)
        if m:
            return m.group(1)
    return None


@dataclass
class JournalRecord:
    """One journal heading plus its field list (for diversity / history)."""

    day: str
    theme: str
    status: str
    title: str = ""
    filename: str = ""
    description: str = ""
    source: str = ""
    detail: str = ""


_FIELD_LINE = re.compile(r"^- \*\*(?P<key>[^*]+):\*\*\s*(?P<val>.*)$")


def parse_detail_fields(detail: str) -> dict[str, str]:
    """Parse ``key=value; key2=value2`` journal Detail lines."""
    out: dict[str, str] = {}
    for part in (detail or "").split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        key, val = part.split("=", 1)
        key = key.strip().lower()
        if key:
            out[key] = val.strip()
    return out


def find_record_for_path(project_root: Path, image: Path | None) -> JournalRecord | None:
    """Latest journal record whose file matches *image* (basename, then resolved path)."""
    if image is None:
        return None
    want_name = Path(image).name.lower()
    if not want_name:
        return None
    want_resolved: Path | None
    try:
        want_resolved = Path(image).resolve() if Path(image).is_file() else None
    except OSError:
        want_resolved = None
    last: JournalRecord | None = None
    for rec in iter_journal_records(project_root):
        raw = (rec.filename or "").strip().strip("`")
        if not raw:
            continue
        p = Path(raw)
        if p.name.lower() == want_name:
            last = rec
            continue
        if want_resolved is None:
            continue
        try:
            if p.is_file() and p.resolve() == want_resolved:
                last = rec
        except OSError:
            continue
    return last


def iter_journal_records(project_root: Path) -> list[JournalRecord]:
    """Parse all journal blocks in order (oldest first)."""
    path = journal_path(Path(project_root))
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    records: list[JournalRecord] = []
    for block in re.split(r"(?=^## )", text, flags=re.M):
        lines = block.splitlines()
        if not lines:
            continue
        hm = _HEADING.match(lines[0])
        if not hm:
            continue
        fields: dict[str, str] = {}
        for line in lines[1:]:
            fm = _FIELD_LINE.match(line.strip())
            if fm:
                fields[fm.group("key").strip().lower()] = fm.group("val").strip()
        rec = JournalRecord(
            day=hm.group("day"),
            theme=hm.group("theme"),
            status=hm.group("status"),
            title=fields.get("title", ""),
            filename=fields.get("file", "").strip("`"),
            description=fields.get("description", ""),
            source=fields.get("source", ""),
            detail=fields.get("detail", ""),
        )
        records.append(rec)
    return records
