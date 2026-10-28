"""Daily 3-theme wallpaper pipeline: GTM | literary | painting."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from rotator.config import Config, PROJECT_ROOT
from rotator.core import apply_image
from rotator.gtm_render import render_gtm_infographic
from rotator.journal import (
    JournalEntry,
    append_entry,
    find_entry_file,
    has_active_for_day,
    iter_journal_records,
    last_creative_theme_for_day,
    parse_detail_fields,
)
from rotator.state import today_in_tz
from rotator.xai_chat import chat_json
from rotator.xai_image import resolve_xai_api_key, save_generated

log = logging.getLogger(__name__)

THEMES = ("gtm", "literary", "painting")


def _content_moderated(exc: BaseException) -> bool:
    """Imagine refused the image. A billing or network error is not this."""
    return "content-moderated" in str(exc).lower()

# User preference: never default to cyberpunk (neon megacity, holographic rain, etc.)
# unless they explicitly request it in a future CLI flag / prompt.
STYLE_BAN = (
    "STYLE BAN (strict): Do NOT use cyberpunk, neon megacity, holographic UI, "
    "blade-runner rain streets, acid pink/green neon noir, or dystopian digital decay. "
    "Prefer painterly, classical, natural light, historical, pastoral, quiet modern, "
    "impressionist, ink wash, or period-appropriate reimaginings. "
    "Only use cyberpunk if the user has explicitly asked for it (they have not)."
)

# Rotate GTM *kind* so we don't cluster on design/home brands.
# Index by day so midnight jobs stay varied without user input.
GTM_FOCUS_ROTATION = (
    "B2B SaaS / enterprise software (e.g. DocuSign, Salesforce, HubSpot, Atlassian, Snowflake)",
    "B2B infrastructure / developer tools (e.g. Stripe, Twilio, Datadog, MongoDB, GitHub)",
    "D2C / consumer brand outside home-decor (e.g. Nike DTC, Warby Parker, Glossier, Allbirds)",
    "Marketplace / platform (e.g. Airbnb hosts side, Etsy sellers, Uber drivers+riders as GTM)",
    "Fintech / payments / insurance (e.g. Square/Block, Robinhood, Lemonade, PayPal)",
    "Healthcare / biotech GTM (e.g. Teladoc, Oscar, Moderna commercial — high-level only)",
    "Consumer media / entertainment product (e.g. Netflix, Spotify, Disney+ as a segment)",
    "Industrial / hardware / climate or auto (e.g. Tesla energy or vehicle retail, Siemens segment)",
    "Food / CPG / retail chain GTM (e.g. Starbucks, Costco membership, Chipotle)",
    "Edtech or productivity (e.g. Duolingo, Coursera, Notion, Monday.com)",
)

# Literary: rotate *canon* so Grok does not collapse onto the same 8 climaxes.
# Ban window is theme-specific (journal), not mixed last-12 index titles.
LITERARY_FOCUS_ROTATION = (
    "Ancient epic or sacred narrative — a specific episode from Iliad, Odyssey, Aeneid, "
    "Gilgamesh, Ramayana, Mahabharata, or Beowulf (not a generic melee)",
    "Shakespeare or early-modern drama — one staged climax (Hamlet, Lear, Macbeth, "
    "Othello, The Tempest, Doctor Faustus); not a portrait of the playwright",
    "18th-century / Enlightenment tale (Candide, Tom Jones, Dangerous Liaisons, "
    "Robinson Crusoe, Gulliver — one concrete incident)",
    "French or German 19th-c novel (Les Misérables, Madame Bovary, The Red and the Black, "
    "Germinal, Faust, Effi Briest) — not Brontë/Austen/Wilde/Shelley/Melville",
    "American 19th-c other than Moby-Dick (Scarlet Letter, Huck Finn, Uncle Tom's Cabin, "
    "Little Women, Leaves of Grass as a scene, Portrait of a Lady)",
    "Victorian English other than Wuthering Heights / Jane Eyre / Pride and Prejudice / "
    "Dorian Gray / Frankenstein (Great Expectations, Tess, Middlemarch, Vanity Fair, "
    "Dracula, Treasure Island, Bleak House)",
    "Modernist 1900–1945 (one episode of Ulysses, Mrs Dalloway, The Great Gatsby, "
    "The Trial, To the Lighthouse, The Sound and the Fury, As I Lay Dying)",
    "World literature outside the Anglo-American school-canon (Tale of Genji, Dream of "
    "the Red Chamber, One Hundred Years of Solitude, Things Fall Apart, Journey to the "
    "West, The God of Small Things, Pedro Páramo)",
    "Postwar / late-20th classic (Beloved, The Handmaid's Tale, Never Let Me Go, "
    "Midnight's Children, The Name of the Rose, Blindness, The Unbearable Lightness of Being)",
    "Epic poem or verse drama (Paradise Lost, Divine Comedy — one canto's incident, "
    "Rime of the Ancient Mariner, The Waste Land as a scene only if concrete, Metamorphoses)",
)

LITERARY_PAINTER_ROTATION = (
    "Spanish masters: Goya, Velázquez, Sorolla, Zurbarán — not Rembrandt or Turner",
    "French Impressionist / Post-Impressionist: Monet, Morisot, Cassatt, Cézanne, Degas, "
    "Toulouse-Lautrec — Van Gogh brushwork OK only if the scene is NOT Starry Night's sky",
    "American: Hopper, Sargent, Wyeth, Winslow Homer, Frederic Church, Rockwell Kent",
    "Italian besides Caravaggio: Titian, Artemisia Gentileschi, Canaletto, Tiepolo, Giotto",
    "Northern / German besides Rembrandt: Vermeer, Bosch, Bruegel, Caspar David Friedrich, "
    "Dürer, Holbein",
    "East Asian style-only: Hokusai, Hiroshige, Sesshū, Guo Xi — literary subject stays the book's",
    "Pre-Raphaelite / Symbolist: Millais, Waterhouse, Redon, Gustave Moreau, Burne-Jones",
    "Quiet 20th-c figurative: Hopper (if not used recently), Andrew Wyeth, Magritte's clarity "
    "(not melting clocks), Frida Kahlo's intimate realism, Lucian Freud flesh — no cubist mashup",
)

PAINTING_FOCUS_ROTATION = (
    "Italian Renaissance other than Mona Lisa (Botticelli Primavera or Birth of Venus, "
    "Raphael School of Athens, Michelangelo Creation of Adam, Titian Venus of Urbino, "
    "Uccello Hunt in the Forest, Piero della Francesca)",
    "Northern Renaissance (van Eyck Arnolfini Portrait, Bosch Garden of Earthly Delights, "
    "Bruegel Hunters in the Snow, Holbein The Ambassadors, Dürer self-portrait, "
    "Altdorfer Battle of Alexander)",
    "Baroque / Dutch Golden Age other than Girl with a Pearl Earring (Rembrandt Night Watch "
    "or Anatomy Lesson, Velázquez Las Meninas, Gentileschi Judith Slaying Holofernes, "
    "Vermeer The Milkmaid or View of Delft, Rubens Descent from the Cross)",
    "Romanticism (Géricault Raft of the Medusa, Friedrich Wanderer above the Sea of Fog, "
    "Delacroix Liberty Leading the People, Turner Fighting Temeraire, Goya Third of May 1808, "
    "Constable The Hay Wain)",
    "Impressionism / Post other than Starry Night (Manet Luncheon on the Grass or Olympia, "
    "Monet Water Lilies or Rouen Cathedral, Seurat La Grande Jatte, Caillebotte Rainy Day, "
    "Renoir Moulin de la Galette, Cézanne Mont Sainte-Victoire)",
    "Japanese ukiyo-e or East Asian (Hokusai Great Wave, Hiroshige Sudden Shower over "
    "Shin-Ōhashi, Utamaro beauty, Sesshū landscape, Sharaku actor print)",
    "American other than American Gothic and Whistler's Mother (Hopper Nighthawks, "
    "Wyeth Christina's World, Copley Watson and the Shark, Church Heart of the Andes, "
    "Homer The Gulf Stream, Sargent Carnation Lily Lily Rose)",
    "20th-c other than Persistence of Memory and Klimt's The Kiss (Munch The Scream, "
    "Picasso Guernica, Mondrian Composition, Chagall I and the Village, Magritte Son of Man, "
    "Kahlo The Two Fridas, Matisse Dance, Rousseau The Dream)",
    "Medieval / early / manuscript (Giotto Lamentation, Unicorn Tapestries, Book of Kells "
    "carpet page as a scene, Wilton Diptych, Duccio Maestà, icons of Rublev Trinity)",
    "Less-reproduced 18th–19th-c (Fragonard The Swing, Millais Ophelia, Waterhouse Lady of "
    "Shalott, Friedrich Sea of Ice, Friedrich Monk by the Sea, Courbet Burial at Ornans, "
    "Eakins The Gross Clinic)",
)

# Do not recycle a book/canvas until this many unique works exist for that theme.
ART_UNIQUE_BEFORE_REUSE = 30
ART_RECENT_WINDOW = 24
PAINTER_UNIQUE_BEFORE_REUSE = 12
PAINTER_RECENT_WINDOW = 8

# LLM celebrity traps — still banned even inside a matching bucket if already used.
LITERARY_CELEBRITY_TRAPS = (
    "1984 Room 101",
    "Moby-Dick: any Ahab vs the whale climax (harpoon, last strike, dragged under)",
    "The Picture of Dorian Gray: stabbing the portrait",
    "Wuthering Heights: Catherine's deathbed or Heathcliff at the grave",
    "Frankenstein: creature first awakening or the arctic ice chase",
)

PAINTING_CELEBRITY_TRAPS = (
    "The Starry Night",
    "Mona Lisa / La Gioconda",
    "The Kiss (Klimt)",
    "The Persistence of Memory",
    "Girl with a Pearl Earring",
)

# Containment matching for titles (not painters).
_WORK_ALIAS_GROUPS = (
    frozenset({"1984", "nineteen eighty four", "nineteen eighty-four"}),
    frozenset({"moby dick", "moby-dick"}),
    frozenset({"picture of dorian gray", "dorian gray"}),
    frozenset({"starry night", "the starry night"}),
    frozenset({"girl with a pearl earring", "girl with pearl earring"}),
    frozenset({"persistence of memory", "the persistence of memory"}),
    frozenset({"mona lisa", "la gioconda", "la joconde"}),
    frozenset(
        {"whistlers mother", "whistler s mother", "arrangement in grey and black"}
    ),
    frozenset({"frankenstein", "frankenstein or the modern prometheus"}),
    frozenset({"the kiss", "klimt s the kiss", "klimts the kiss"}),
)

_PAINTER_GIVEN_NOISE = frozenset(
    {"john", "jean", "william", "james", "george", "peter", "paul", "hans", "jan"}
)

_COMPANY_ALIAS_GROUPS = (
    frozenset({"square", "block", "square block", "block inc"}),
    frozenset({"alphabet", "google"}),
    frozenset({"meta", "facebook"}),
    frozenset({"x", "twitter"}),
)


@dataclass
class DailyResult:
    success: bool
    message: str
    path: Path | None = None
    theme: str | None = None
    est_cost_usd: float = 0.0
    skipped: bool = False


def theme_for_day(day) -> str:
    """Stable rotation: gtm → literary → painting."""
    return THEMES[day.toordinal() % 3]


def next_theme(theme: str) -> str:
    """Next theme in cycle after *theme* (wraps)."""
    t = (theme or "gtm").lower()
    if t not in THEMES:
        return THEMES[0]
    return THEMES[(THEMES.index(t) + 1) % len(THEMES)]


def resolve_generate_theme(
    day,
    *,
    force: bool,
    theme_override: str | None,
    project_root: Path,
    day_str: str,
) -> str:
    """Pick theme for this generation.

    - Explicit ``--theme`` always wins.
    - First gen of the day: calendar rotation (``theme_for_day``).
    - ``--force`` / desktop New after something already exists today: **next**
      theme after the last creative gen (gtm → literary → painting → …).
    """
    if theme_override:
        return theme_override.lower()

    calendar = theme_for_day(day)
    if not force:
        return calendar

    last = last_creative_theme_for_day(project_root, day_str)
    if last:
        advanced = next_theme(last)
        log.info(
            "Force new: last creative theme today was %s → generating %s",
            last,
            advanced,
        )
        return advanced
    return calendar


def _slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w]+", "_", text.strip().lower()).strip("_")
    return (s[:max_len] or "daily").rstrip("_")


def _dest(cfg: Config, day_str: str, theme: str, slug: str) -> Path:
    name = f"{day_str}_{theme}_{slug}"
    return cfg.grok_daily_dir / f"{name}.png"


def _norm_name(text: str) -> str:
    s = (text or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if s.startswith("the "):
        s = s[4:]
    if s.endswith(" reimagined"):
        s = s[: -len(" reimagined")].strip()
    return s


def _same_work(a: str, b: str) -> bool:
    """True if two book/painting titles refer to the same work."""
    na, nb = _norm_name(a), _norm_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    for group in _WORK_ALIAS_GROUPS:
        norms = {_norm_name(x) for x in group}
        if na in norms and nb in norms:
            return True
    # Long-title containment ("picture of dorian gray" vs "dorian gray").
    # Skip short tokens so "kiss" does not match unrelated scenes.
    if min(len(na), len(nb)) >= 10 and (na in nb or nb in na):
        return True
    return False


def _painter_tokens(name: str) -> set[str]:
    stop = {"van", "von", "de", "da", "del", "della", "di", "le", "la", "the", "and", "of"}
    return {
        p
        for p in _norm_name(name).split()
        if p not in stop and len(p) > 2
    }


def _same_painter(a: str, b: str) -> bool:
    ta, tb = _painter_tokens(a), _painter_tokens(b)
    if not ta or not tb:
        return False
    overlap = ta & tb
    if overlap - _PAINTER_GIVEN_NOISE:
        return True
    return False


def _dedupe_keep(names: list[str], same) -> list[str]:
    out: list[str] = []
    for n in names:
        if n and not any(same(n, x) for x in out):
            out.append(n)
    return out


def _ban_from_used(
    used: list[str],
    same,
    *,
    min_unique: int,
    window: int,
) -> list[str]:
    unique = _dedupe_keep(used, same)
    if len(unique) < min_unique:
        return unique
    return unique[-window:]


def _name_is_banned(candidate: str, banned: list[str], same) -> bool:
    if not (candidate or "").strip():
        return False
    return any(same(candidate, b) for b in banned)


def _bucket_for_day(day_str: str, buckets: tuple[str, ...], nudge: int = 0) -> str:
    n = sum(ord(c) for c in day_str) + int(day_str.replace("-", "")[-4:] or 0) + nudge
    return buckets[n % len(buckets)]


def _same_day_nudge(cfg: Config, day_str: str, theme: str) -> int:
    if not cfg.grok_daily_dir.is_dir():
        return 0
    return len(list(cfg.grok_daily_dir.glob(f"{day_str}_{theme}_*")))


def _records_for_theme(root: Path, theme: str):
    return [r for r in iter_journal_records(root) if r.theme == theme]


def _literary_used(root: Path) -> tuple[list[str], list[str], list[str]]:
    books, moments, painters = [], [], []
    for rec in _records_for_theme(root, "literary"):
        fields = parse_detail_fields(rec.detail)
        book = fields.get("book") or (
            rec.title.split(" — ", 1)[0].strip() if " — " in rec.title else rec.title
        )
        moment = rec.title.split(" — ", 1)[1].strip() if " — " in rec.title else ""
        painter = fields.get("painter") or ""
        if book:
            books.append(book)
        if moment:
            moments.append(moment)
        if painter:
            painters.append(painter)
    return books, moments, painters


def _company_brand(name: str) -> str:
    s = (name or "").strip()
    for sep in (" — ", " – ", " - "):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
            break
    return _norm_name(s)


def _same_company(a: str, b: str) -> bool:
    """Brand-level match: Tesla vs Tesla Energy, Lemonade vs Lemonade."""
    na, nb = _company_brand(a), _company_brand(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    for group in _COMPANY_ALIAS_GROUPS:
        norms = {_norm_name(x) for x in group}
        if na in norms and nb in norms:
            return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    # "tesla" vs "tesla energy" — require a following space so "canva" ≠ "canvas"
    if " " in longer and longer.startswith(shorter + " "):
        return True
    return False


def _gtm_used(root: Path) -> list[str]:
    companies: list[str] = []
    for rec in _records_for_theme(root, "gtm"):
        fields = parse_detail_fields(rec.detail)
        company = fields.get("company") or (
            rec.title.split(" — ", 1)[0].strip() if rec.title else ""
        )
        if company:
            companies.append(company)
    return companies


def _gtm_bans(root: Path) -> dict[str, list[str]]:
    companies = _gtm_used(root)
    return {
        "companies": _ban_from_used(
            companies,
            _same_company,
            min_unique=ART_UNIQUE_BEFORE_REUSE,
            window=ART_RECENT_WINDOW,
        ),
    }


def _gtm_hits_ban(data: dict, bans: dict[str, list[str]]) -> str | None:
    company = str(data.get("company") or "")
    segment = str(data.get("segment") or "") or ""
    if _name_is_banned(company, bans["companies"], _same_company):
        return f"company={company}"
    if segment and _name_is_banned(segment, bans["companies"], _same_company):
        return f"segment={segment}"
    for banned in bans["companies"]:
        bs = _slug(banned, max_len=24)
        slug = _slug(company if not segment else f"{company}_{segment}")
        if bs and len(bs) >= 5 and bs in slug:
            return f"slug~{banned}"
    return None


def _painting_used(root: Path) -> tuple[list[str], list[str]]:
    titles, artists = [], []
    for rec in _records_for_theme(root, "painting"):
        fields = parse_detail_fields(rec.detail)
        title = rec.title
        if title.lower().endswith(" reimagined"):
            title = title[: -len(" reimagined")].strip()
        artist = fields.get("artist") or fields.get("original_artist") or ""
        if title:
            titles.append(title)
        if artist:
            artists.append(artist)
    return titles, artists


def _literary_bans(root: Path) -> dict[str, list[str]]:
    books, moments, painters = _literary_used(root)
    return {
        "books": _ban_from_used(
            books,
            _same_work,
            min_unique=ART_UNIQUE_BEFORE_REUSE,
            window=ART_RECENT_WINDOW,
        ),
        "moments": _dedupe_keep(moments[-ART_RECENT_WINDOW:], _same_work),
        "painters": _ban_from_used(
            painters,
            _same_painter,
            min_unique=PAINTER_UNIQUE_BEFORE_REUSE,
            window=PAINTER_RECENT_WINDOW,
        ),
    }


def _painting_bans(root: Path) -> dict[str, list[str]]:
    titles, artists = _painting_used(root)
    return {
        "titles": _ban_from_used(
            titles,
            _same_work,
            min_unique=ART_UNIQUE_BEFORE_REUSE,
            window=ART_RECENT_WINDOW,
        ),
        "artists": _ban_from_used(
            artists,
            _same_painter,
            min_unique=PAINTER_UNIQUE_BEFORE_REUSE,
            window=PAINTER_RECENT_WINDOW,
        ),
    }


def _literary_hits_ban(data: dict, bans: dict[str, list[str]]) -> str | None:
    book = str(data.get("book") or "")
    painter = str(data.get("painter") or "")
    moment = str(data.get("moment_title") or "")
    slug = str(data.get("slug") or "")
    if _name_is_banned(book, bans["books"], _same_work):
        return f"book={book}"
    if moment and _name_is_banned(moment, bans["moments"], _same_work):
        return f"moment={moment}"
    if _name_is_banned(painter, bans["painters"], _same_painter):
        return f"painter={painter}"
    # Slug still carrying a banned book (e.g. moby_dick_ahab_...)
    for banned in bans["books"]:
        bs = _slug(banned, max_len=24)
        if bs and len(bs) >= 8 and bs in _slug(slug or book):
            return f"slug~{banned}"
    return None


def _painting_hits_ban(data: dict, bans: dict[str, list[str]]) -> str | None:
    title = str(data.get("original_title") or "")
    artist = str(data.get("original_artist") or "")
    slug = str(data.get("slug") or "")
    if _name_is_banned(title, bans["titles"], _same_work):
        return f"painting={title}"
    if _name_is_banned(artist, bans["artists"], _same_painter):
        return f"artist={artist}"
    for banned in bans["titles"]:
        bs = _slug(banned, max_len=24)
        if bs and len(bs) >= 8 and bs in _slug(slug or title):
            return f"slug~{banned}"
    return None


def _chat_plan(
    system: str,
    user: str,
    *,
    root: Path,
    day_str: str,
    note: str,
    temperature: float = 0.5,
) -> tuple[dict, float]:
    data = None
    cost = 0.0
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            data, ev = chat_json(
                system,
                user
                + (
                    "\nRespond with a single JSON object only, no markdown fences."
                    if attempt
                    else ""
                ),
                project_root=root,
                day_ist=day_str,
                note=note + (f"-retry{attempt}" if attempt else ""),
                temperature=temperature,
            )
            cost = ev.est_usd
            break
        except Exception as e:
            last_err = e
            log.warning("%s attempt %s failed: %s", note, attempt + 1, e)
    if data is None:
        raise RuntimeError(f"{note} failed: {last_err}") from last_err
    return data, cost


def generate_daily(
    cfg: Config,
    *,
    force: bool = False,
    theme_override: str | None = None,
    set_wallpaper: bool = True,
    project_root: Path | None = None,
    force_original: str | None = None,
) -> DailyResult:
    """Create a themed wallpaper for today (unless already done without force).

    With ``force=True`` (desktop **New**), advances to the **next** theme after
    the last creative generation today instead of repeating the same theme.
    """
    root = Path(project_root or PROJECT_ROOT)
    day = today_in_tz(cfg.timezone)
    day_str = day.isoformat()
    theme = resolve_generate_theme(
        day,
        force=force,
        theme_override=theme_override,
        project_root=root,
        day_str=day_str,
    )
    if theme not in THEMES:
        return DailyResult(False, f"Unknown theme {theme!r}; use {THEMES}")

    if not force and has_active_for_day(root, day_str):
        existing = find_entry_file(root, day_str)
        msg = (
            f"Already have today's wallpaper ({day_str}). "
            f"Use --force (or desktop New) for the next theme. "
            f"Existing: {existing or 'see journal'}"
        )
        log.info(msg)
        return DailyResult(True, msg, skipped=True, theme=theme)

    if theme in {"literary", "painting"} and not resolve_xai_api_key():
        return DailyResult(
            False,
            "XAI_API_KEY required for literary/painting generation. Add it to .env.",
            theme=theme,
        )
    if theme == "gtm" and not resolve_xai_api_key():
        return DailyResult(
            False,
            "XAI_API_KEY required for GTM research (Grok chat). Add it to .env.",
            theme=theme,
        )

    cfg.grok_daily_dir.mkdir(parents=True, exist_ok=True)
    cost_total = 0.0

    try:
        if theme == "gtm":
            path, title, desc, detail, cost_total = _gen_gtm(cfg, root, day_str)
            source = "gtm-code"
        elif theme == "literary":
            path, title, desc, detail, cost_total = _gen_literary(cfg, root, day_str)
            source = "xai-image"
        else:
            path, title, desc, detail, cost_total = _gen_painting(
                cfg, root, day_str, force_original=force_original
            )
            source = "xai-image"
    except Exception as e:
        log.exception("Daily generation failed")
        return DailyResult(False, f"Generation failed: {e}", theme=theme)

    append_entry(
        root,
        JournalEntry(
            day=day_str,
            theme=theme,
            title=title,
            description=desc,
            filename=str(path),
            source=source,
            detail=detail,
            est_cost_usd=cost_total,
            status="active",
        ),
    )

    if set_wallpaper:
        result = apply_image(cfg, path)
        if not result.success:
            return DailyResult(
                False,
                f"Saved {path.name} but set failed: {result.message}",
                path=path,
                theme=theme,
                est_cost_usd=cost_total,
            )
        msg = f"[{theme}] {title} → {path.name} | set OK | est ${cost_total:.4f}"
    else:
        msg = f"[{theme}] {title} → {path.name} | not set | est ${cost_total:.4f}"

    return DailyResult(
        True, msg, path=path, theme=theme, est_cost_usd=cost_total
    )


def _gtm_focus_for_day(day_str: str, nudge: int = 0) -> str:
    """Pick a diversity bucket from the IST date string."""
    return _bucket_for_day(day_str, GTM_FOCUS_ROTATION, nudge)


def _gen_gtm(cfg: Config, root: Path, day_str: str):
    bans = _gtm_bans(root)
    force_nudge = _same_day_nudge(cfg, day_str, "gtm")
    focus = _gtm_focus_for_day(day_str, force_nudge)

    system = (
        "You are a precise GTM strategist teaching an operator who wants BROAD exposure "
        "across industries and business models (B2B, D2C, marketplaces, fintech, media, etc.). "
        "Return ONLY valid JSON. Use real-world GTM knowledge of famous companies.\n"
        "HARD RULES:\n"
        "- NEVER invent brands; only real, widely known companies.\n"
        "- NEVER default to wallpaper, wall art, interior design, home-decor, paint, "
        "or 'design tool for wallpapers' angles — this app is a desktop wallpaper tool "
        "but the SUBJECT companies must NOT be wallpaper/home-decor brands.\n"
        "- Avoid clustering on pure design tools (Canva/Figma/Adobe) unless the focus "
        "bucket explicitly asks for productivity/design software.\n"
        "- Conglomerates (Amazon, Google, Meta, Microsoft, Apple): one product/segment only "
        "(e.g. AWS, Prime Video, YouTube, Instagram) — never the whole empire.\n"
        "- Focused companies: map the full channel mix (inbound, outbound, partner, sales, "
        "events, PLG, community as relevant).\n"
        "- Prefer variety: different industries day to day. NEVER reuse a company already mapped."
    )
    user = (
        "Create ONE GTM channel map for a desktop learning wallpaper (infographic content only).\n"
        f"TODAY'S REQUIRED FOCUS BUCKET (must match): {focus}\n"
        f"HARD BAN — do not reuse these companies or their segments: {bans['companies']}\n"
        "Also avoid companies whose core product is: wallpaper, murals, home paint, "
        "interior stickers, or similar home-surface goods.\n\n"
        "Return JSON with keys:\n"
        "{\n"
        '  "company": string (canonical brand name),\n'
        '  "segment": string or null,\n'
        '  "industry": string (e.g. "B2B SaaS", "D2C apparel", "fintech"),\n'
        '  "business_model": string (e.g. "enterprise sales-led", "PLG", "marketplace"),\n'
        '  "complexity": "simple" | "segment",\n'
        '  "headline": short subtitle about GTM, not product marketing fluff,\n'
        '  "narrative": 1-2 sentences how demand becomes revenue,\n'
        '  "description": 2-4 sentences for a journal — what a GTM learner should notice;\n'
        "                 do NOT mention desktop wallpapers as a product category,\n"
        '  "channels": [\n'
        '     {"name": "Inbound", "role": "...", "tactics": ["...", "..."]},\n'
        "     ... 4 to 6 channels appropriate to THIS company\n"
        "  ]\n"
        "}\n"
    )
    data: dict | None = None
    cost = 0.0
    for round_i in range(2):
        plan_user = user
        if round_i and data:
            hit = _gtm_hits_ban(data, bans)
            plan_user += (
                f"\nPREVIOUS PLAN REJECTED ({hit}). "
                "Pick a different real company in today's focus bucket. "
                "Do not reuse anything on the HARD BAN list.\n"
            )
        data, c = _chat_plan(
            system,
            plan_user,
            root=root,
            day_str=day_str,
            note=f"gtm-research:{focus[:40]}"
            + (f"-diversity{round_i}" if round_i else ""),
            temperature=0.5,
        )
        cost += c
        hit = _gtm_hits_ban(data, bans)
        if not hit:
            break
        log.warning("gtm plan reused banned company (%s); retrying", hit)
    company = str(data.get("company") or "Company")
    segment = data.get("segment")
    slug_base = company if not segment else f"{company}_{segment}"
    dest = _dest(cfg, day_str, "gtm", _slug(slug_base))
    # Unique path if regenerating same company slug
    if dest.exists():
        dest = dest.with_name(f"{dest.stem}_{force_nudge + 1}{dest.suffix}")
    path = render_gtm_infographic(data, dest)
    title = company if not segment else f"{company} — {segment}"
    desc = str(data.get("description") or data.get("narrative") or title)
    industry = data.get("industry") or "?"
    model = data.get("business_model") or "?"
    detail = (
        f"company={company}; industry={industry}; model={model}; "
        f"complexity={data.get('complexity')}; "
        f"channels={len(data.get('channels') or [])}; focus={focus[:50]}"
    )
    return path, title, desc, detail, cost


def _gen_literary(
    cfg: Config,
    root: Path,
    day_str: str,
    *,
    forced_scene: dict | None = None,
):
    """Literary climax in a famous painter's *style* (not a painting reimagining).

    forced_scene: optional override dict with book/author/moment_title/etc. for tests.
    """
    bans = _literary_bans(root)
    nudge = _same_day_nudge(cfg, day_str, "literary")
    focus = _bucket_for_day(day_str, LITERARY_FOCUS_ROTATION, nudge)
    painter_focus = _bucket_for_day(day_str, LITERARY_PAINTER_ROTATION, nudge + 3)
    system = (
        "You pick great literature and describe a single iconic climax or best scene "
        "for a 16:9 desktop wallpaper. Spoilers are OK. No text/titles in the image. "
        f"{STYLE_BAN} "
        "CRITICAL ART DIRECTION: Choose ONE famous fine-art painter and render the "
        "literary scene entirely in that painter's visual style (brushwork, palette, "
        "light, composition habits). "
        "This is NOT 'reimagine a famous painting as the book scene' and NOT a mashup "
        "where the painting's subject matter replaces the book. "
        "Keep the literary characters, setting, and moment from the book; only the "
        "painter's style/technique applies. "
        "HARD DIVERSITY: do not default to the same school-canon climaxes "
        "(Room 101, Ahab vs the whale, Dorian stabbing the portrait, Catherine's "
        "grave/deathbed, Frankenstein on the ice). Rotate authors, languages, and centuries. "
        "Return ONLY JSON."
    )
    user = (
        "Choose a major book and one pivotal scene, plus one famous painter whose "
        "STYLE will paint that scene.\n"
        f"TODAY'S REQUIRED LITERATURE BUCKET (must match): {focus}\n"
        f"TODAY'S REQUIRED PAINTER BUCKET (must match): {painter_focus}\n"
        f"HARD BAN — do not reuse these books (any scene): {bans['books']}\n"
        f"HARD BAN — do not reuse these painters: {bans['painters']}\n"
        f"Also skip these already-used moments: {bans['moments']}\n"
        f"Celebrity traps (skip; they have been overused): {list(LITERARY_CELEBRITY_TRAPS)}\n"
        "Do not turn the image into a remix of a known canvas subject; the narrative "
        "must remain the book's climax.\n"
        "JSON keys:\n"
        '  "book", "author", "moment_title",\n'
        '  "painter", "painter_style_notes" (what traits of that painter to apply),\n'
        '  "scene_prompt" (detailed visual prompt: literary scene + in the style of '
        "the named painter, no words in scene),\n"
        '  "description" (2-4 sentences for journal, spoilers OK; mention painter style),\n'
        '  "slug"\n'
    )
    if forced_scene:
        user = (
            "Create a literary wallpaper plan for this FIXED scene (do not change book/moment):\n"
            f"{forced_scene}\n"
            "Choose ONE famous painter and apply only their visual style to this exact "
            "literary moment (not a reimagining of one of their paintings' subjects).\n"
            f"Prefer painter bucket: {painter_focus}\n"
            f"HARD BAN painters (pick someone else unless the fixed scene requires them): "
            f"{bans['painters']}\n"
            f"{STYLE_BAN}\n"
            "JSON keys: book, author, moment_title, painter, painter_style_notes, "
            "scene_prompt, description, slug\n"
        )
    data: dict | None = None
    cost = 0.0
    for round_i in range(2):
        plan_user = user
        if round_i and data and not forced_scene:
            hit = _literary_hits_ban(data, bans)
            plan_user += (
                f"\nPREVIOUS PLAN REJECTED ({hit}). "
                "Pick a different book from today's literature bucket and a painter "
                "from today's painter bucket. Do not reuse anything on the HARD BAN lists.\n"
            )
        data, c = _chat_plan(
            system,
            plan_user,
            root=root,
            day_str=day_str,
            note="literary-plan" + (f"-diversity{round_i}" if round_i else ""),
            temperature=0.85,
        )
        cost += c
        if forced_scene:
            break
        hit = _literary_hits_ban(data, bans)
        if not hit:
            break
        log.warning("literary plan reused banned work (%s); retrying", hit)

    if forced_scene:
        for k in ("book", "author", "moment_title"):
            if forced_scene.get(k):
                data[k] = forced_scene[k]

    def _scene_prompt(plan: dict) -> tuple[str, str]:
        prompt = str(plan.get("scene_prompt") or "")
        painter_name = str(plan.get("painter") or "a classical master")
        style_notes = str(plan.get("painter_style_notes") or "")
        for bad in (
            "cyberpunk",
            "Cyberpunk",
            "neon megacity",
            "holographic",
            "blade runner",
            "Blade Runner",
        ):
            prompt = prompt.replace(bad, "painterly")
        prompt += (
            f" Painted in the distinctive fine-art style of {painter_name}"
            f"{(': ' + style_notes) if style_notes else ''}. "
            "This is a literary scene from the book, not a recreation of one of the "
            "painter's famous canvases. "
            "16:9 cinematic desktop wallpaper, museum-quality painterly finish, "
            "main subject concentrated in the center with soft low-detail margins "
            "left and right for desktop icons, "
            "no cyberpunk, no neon megacity, no holographic UI, "
            "no text, no logos, no watermark, no UI."
        )
        return prompt, painter_name

    def _scene_dest(plan: dict, painter_name: str) -> tuple[Path, str, str]:
        scene_slug = _slug(str(plan.get("slug") or plan.get("moment_title") or "scene"))
        painter_bit = _slug(painter_name, max_len=24)
        dest = cfg.grok_daily_dir / f"{day_str}_literary_{scene_slug}_{painter_bit}.jpg"
        if dest.exists():
            dest = (
                cfg.grok_daily_dir
                / f"{day_str}_literary_{scene_slug}_{painter_bit}_v2.jpg"
            )
        return dest, scene_slug, painter_bit

    prompt, painter = _scene_prompt(data)
    dest, slug, painter_slug = _scene_dest(data, painter)
    try:
        path = save_generated(
            prompt,
            dest,
            project_root=root,
            day_ist=day_str,
            note=f"literary:{slug}:{painter_slug}",
        )
    except RuntimeError as e:
        if not _content_moderated(e):
            raise
        log.warning("literary image moderated (%s); replanning a quieter scene", slug)
        reject = (
            "\nPREVIOUS IMAGE REJECTED by content moderation "
            f"(book={data.get('book')!r}, moment={data.get('moment_title')!r}, "
            f"painter={data.get('painter')!r}). "
            "Imagine rejects nudity, sexual content, and gore. "
        )
        if forced_scene:
            reject += (
                "Keep this same book and moment. Rewrite scene_prompt so every figure "
                "is fully clothed and the picture has no blood, corpse, or sexual content.\n"
            )
        else:
            reject += (
                "Pick a DIFFERENT book and a different pivotal scene from today's "
                "literature bucket, and a painter not on the HARD BAN list. "
                "Choose a quiet moment: no nudity, no sex, no blood, no corpse, "
                "no beheading, no deathbed.\n"
            )
        data, c = _chat_plan(
            system,
            user + reject,
            root=root,
            day_str=day_str,
            note="literary-plan-moderation",
            temperature=0.9,
        )
        cost += c
        if forced_scene:
            for k in ("book", "author", "moment_title"):
                if forced_scene.get(k):
                    data[k] = forced_scene[k]
        prompt, painter = _scene_prompt(data)
        dest, slug, painter_slug = _scene_dest(data, painter)
        try:
            path = save_generated(
                prompt,
                dest,
                project_root=root,
                day_ist=day_str,
                note=f"literary:{slug}:{painter_slug}",
            )
        except RuntimeError as retry_err:
            if _content_moderated(retry_err):
                log.warning("literary moderation retry also blocked (%s)", slug)
            raise
    from rotator.costs import estimate_image_usd

    cost += estimate_image_usd(1)
    title = f"{data.get('book', 'Book')} — {data.get('moment_title', 'Scene')}"
    desc = str(data.get("description") or title)
    detail = (
        f"author={data.get('author')}; book={data.get('book')}; "
        f"painter={painter}; style_only=true"
    )
    return path, title, desc, detail, cost


def _gen_painting(
    cfg: Config, root: Path, day_str: str, *, force_original: str | None = None
):
    bans = _painting_bans(root)
    nudge = _same_day_nudge(cfg, day_str, "painting")
    focus = _bucket_for_day(day_str, PAINTING_FOCUS_ROTATION, nudge)
    system = (
        "You reimagine famous paintings for a 16:9 desktop wallpaper. "
        "Keep composition echo so the original is recognizable, but reimagine medium/era/setting. "
        f"{STYLE_BAN} "
        "Good reimagine directions: different century, season, climate, medium "
        "(watercolor, fresco, stained glass, charcoal), quiet modern interior, "
        "natural landscape transplant — never cyberpunk by default. "
        "HARD DIVERSITY: do not default to Starry Night, Mona Lisa, Klimt's The Kiss, "
        "Persistence of Memory, or Girl with a Pearl Earring. Rotate period and geography. "
        "HARD MODERATION: Imagine rejects nudes, sexualized bodies, and gore. "
        "You MAY pick famous nudes (Birth of Venus, Venus of Urbino, Olympia, "
        "Creation of Adam, Primavera) — that is the point of a reimagining — "
        "but the image_prompt must fully clothe every figure (linen, robes, "
        "period dress). Keep pose, grouping, and setting recognizable. "
        "Do NOT describe bare skin, breasts, genitals, or 'after the original nude'. "
        "Gore still fails clothing: skip beheadings, dismemberment, surgery, "
        "massacre close-ups (Judith Slaying Holofernes, Anatomy Lesson corpse, "
        "Gross Clinic, Third of May execution detail). "
        "No text on image. Return ONLY JSON."
    )
    user = (
        "Pick a famous painting and a reimagining direction.\n"
        f"TODAY'S REQUIRED ART-HISTORY BUCKET (must match): {focus}\n"
        f"HARD BAN — do not reuse these original paintings: {bans['titles']}\n"
        f"HARD BAN — do not reuse these original artists: {bans['artists']}\n"
        f"Celebrity traps (skip; they have been overused): {list(PAINTING_CELEBRITY_TRAPS)}\n"
        "FORBIDDEN directions unless user asked: cyberpunk, neon city, holograms, "
        "blade runner, dystopian tech noir.\n"
        "JSON keys:\n"
        '  "original_title", "original_artist", "reimagine_direction", '
        '"image_prompt" (full visual prompt), "description" (journal 2-4 sentences), "slug"\n'
    )
    if force_original:
        user += (
            f"\nMUST pick original_title={force_original!r}. "
            "Fully clothe every figure in image_prompt; keep pose and setting recognizable.\n"
        )
    data: dict | None = None
    cost = 0.0
    for round_i in range(2):
        plan_user = user
        if round_i and data:
            hit = _painting_hits_ban(data, bans)
            plan_user += (
                f"\nPREVIOUS PLAN REJECTED ({hit}). "
                "Pick a different original painting from today's art-history bucket "
                "and a different artist. Do not reuse HARD BAN lists.\n"
            )
        data, c = _chat_plan(
            system,
            plan_user,
            root=root,
            day_str=day_str,
            note="painting-plan" + (f"-diversity{round_i}" if round_i else ""),
            temperature=0.85,
        )
        cost += c
        hit = _painting_hits_ban(data, bans)
        if not hit:
            break
        log.warning("painting plan reused banned work (%s); retrying", hit)
    prompt = str(data.get("image_prompt") or "")
    # Strip accidental cyberpunk leakage from model output before image gen
    for bad in (
        "cyberpunk",
        "Cyberpunk",
        "neon megacity",
        "holographic",
        "blade runner",
        "Blade Runner",
        "neon-lit",
        "neon lit",
        "acid green",
        "electric pink",
    ):
        prompt = prompt.replace(bad, "painterly")
    prompt += (
        " 16:9 desktop wallpaper, high detail artistic reimagining, "
        "primary composition centered with calm quieter edges left and right "
        "so desktop icons remain readable, "
        "fully clothed figures only, no nudity, no gore, "
        "no cyberpunk, no neon dystopia, no holographic interfaces, "
        "no text, no logos, no watermark."
    )
    slug = _slug(str(data.get("slug") or data.get("original_title") or "painting"))
    dest = cfg.grok_daily_dir / f"{day_str}_painting_{slug}.jpg"
    log.info(
        "painting Imagine attempt: %s / %s",
        data.get("original_title"),
        data.get("original_artist"),
    )
    try:
        path = save_generated(
            prompt,
            dest,
            project_root=root,
            day_ist=day_str,
            note=f"painting:{slug}",
        )
    except RuntimeError as e:
        if not _content_moderated(e):
            raise
        log.warning("painting image moderated (%s); replanning clothed/landscape work", slug)
        data, c = _chat_plan(
            system,
            user
            + "\nPREVIOUS IMAGE REJECTED by content moderation "
            f"(original_title={data.get('original_title')!r}). "
            "If that canvas is a nude, you already should have clothed it — "
            "now pick a DIFFERENT original from today's bucket "
            "(architecture, landscape, or clothed group). No gore.\n",
            root=root,
            day_str=day_str,
            note="painting-plan-moderation",
            temperature=0.9,
        )
        cost += c
        prompt = str(data.get("image_prompt") or "")
        for bad in (
            "cyberpunk",
            "Cyberpunk",
            "neon megacity",
            "holographic",
            "blade runner",
            "Blade Runner",
            "neon-lit",
            "neon lit",
            "acid green",
            "electric pink",
        ):
            prompt = prompt.replace(bad, "painterly")
        prompt += (
            " 16:9 desktop wallpaper, high detail artistic reimagining, "
            "primary composition centered with calm quieter edges left and right "
            "so desktop icons remain readable, "
            "fully clothed figures only, no nudity, no gore, "
            "no cyberpunk, no neon dystopia, no holographic interfaces, "
            "no text, no logos, no watermark."
        )
        slug = _slug(str(data.get("slug") or data.get("original_title") or "painting"))
        dest = cfg.grok_daily_dir / f"{day_str}_painting_{slug}.jpg"
        try:
            path = save_generated(
                prompt,
                dest,
                project_root=root,
                day_ist=day_str,
                note=f"painting:{slug}",
            )
        except RuntimeError as retry_err:
            if _content_moderated(retry_err):
                log.warning("painting moderation retry also blocked (%s)", slug)
            raise
    from rotator.costs import estimate_image_usd

    cost += estimate_image_usd(1)
    title = f"{data.get('original_title', 'Painting')} reimagined"
    desc = str(data.get("description") or title)
    detail = (
        f"artist={data.get('original_artist')}; "
        f"direction={data.get('reimagine_direction')}"
    )
    return path, title, desc, detail, cost
