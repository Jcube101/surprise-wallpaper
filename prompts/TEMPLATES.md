# Prompt templates (legacy + notes)

> **Current product** uses `rotator/daily.py` for three themes (gtm / literary / painting).  
> This file is kept as optional creative reference and for agent improvisation **outside** the default pipeline.

---

## Live themes (source of truth in code)

### GTM

- Research via xAI chat → JSON channels  
- Render via Pillow (center-safe, no meta text)  
- Diversity buckets + ban on wallpaper/home-decor **subjects**  
- See `rotator/daily.py` → `_gen_gtm`

### Literary

Agent / chat plan should produce:

- Book, author, moment title  
- **Famous painter** + style notes (style only — not a mashup of that painter’s famous canvas as the plot)  
- Visual scene prompt: literary scene *in the style of* the painter; 16:9, center subject, quiet edges, **no text in image**  
- Journal description (spoilers OK; mention painter)

### Painting

- Original work + artist + reimagine direction  
- Visual prompt: 16:9, center composition, quiet edges, no text  
- Journal description  
- **No cyberpunk by default** (user preference) — only if they ask

---

## One-line user phrases (still useful)

- `python wallpaper.py --new`  
- `Surprise me with today’s wallpaper` → agent runs CLI or explains theme of the day  
- `I don’t like today` → `python wallpaper.py reject`  
- `Next wallpaper` → `python wallpaper.py next` or desktop right-click  
- `Bring back yesterday` → `python wallpaper.py restore --date YYYY-MM-DD`

---

## Legacy tasteful templates (optional)

Use only if the user explicitly wants a freeform landscape / fantasy image **outside** the three-theme product.

### T1–T4 (examples)

**Misty lake dawn**  
Soft misty lake at dawn, pale lavender and champagne sky, ink-wash mountains, 16:9, center calm horizon, no text.

**Indigo crescent**  
Deep indigo night to dusty rose, crescent moon, soft clouds, 16:9, center moon, quiet edges, no text.

**Sage hills gold**  
Pale sage hills, pearl-grey sky, thin gold horizon ribbon, impressionist, 16:9, no text.

**Pearl horizon**  
Abstract sea/sky pearlescent gradients, minimal, 16:9, no text.

Exact prompts from those seed packs stay in local `USED_BATCH_*.md` notes and are not in git. Prefer the live three-theme pipeline for daily habit.

---

## Agent checklist (if generating outside CLI)

1. Prefer `wallpaper.py --new` so journal + costs stay consistent.  
2. If hand-dropping a file: name `Grok_Daily/YYYY-MM-DD_<theme>_<slug>.jpg` and append journal manually or run `set`.  
3. Never use Bing.  
4. GTM maps: code render only.
