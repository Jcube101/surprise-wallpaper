# SPEC — Grok Surprise Wallpaper Rotator (v2)

## 1. Purpose

Local-first Windows wallpaper system:

- **One active creative image per IST calendar day**
- Themes rotate: **gtm → literary → painting**
- Journal + estimated xAI cost logs
- Reject → NASA APOD; restore past images via CLI
- **No Bing**

## 2. Principles

| Principle | Rule |
|-----------|------|
| One per day | Journal blocks second gen unless `--force` |
| Theme rotation | First gen of day: `THEMES[day.toordinal() % 3]`; **force/New**: next after last creative today |
| GTM readable | Pillow 16:9 infographic; center-safe; no meta chrome |
| GTM diverse | Live Grok research + industry focus buckets + journal company bans; no wallpaper-brand subjects |
| Literary / painting | Grok chat plan + Grok Imagine; center-weighted composition; theme-specific book/canvas/painter bans + focus buckets |
| Offline set | Selection + SPI never require network |
| Explorer path | SPI **and** `CurrentWallpaperPath` so leftover Bing cannot paint black |
| No blank overlay | After set, on logon skip, and every minute, hide a fullscreen Windows Input Experience window |
| No task console | Scheduled tasks execute `pythonw.exe` beside the `python.exe` given to `install_tasks.ps1` |
| Smart dedupe | `.last_set.txt` for set-only path |
| Secrets | `.env` only; never commit keys |

## 3. Architecture

```text
wallpaper.py --new / run_daily_generate.py
        │
        ├─ gtm ──► xAI chat JSON ──► gtm_render (Pillow PNG)
        ├─ literary ──► xAI chat ──► xAI images
        └─ painting ──► xAI chat ──► xAI images
                │
                ▼
        Grok_Daily/YYYY-MM-DD_<theme>_*.{png,jpg}
                │
        journal + costs ──► logs/
                │
                ▼
        SystemParametersInfoW + CurrentWallpaperPath
        + dismiss fullscreen Input Experience overlay (+ optional toast)

reject ──► _rejected/ + NASA APOD ──► Curated/ ──► set
restore ──► copy from _rejected if needed ──► set
```

### Package modules (`rotator/`)

| Module | Role |
|--------|------|
| `config.py` / `envutil.py` | config.json + `.env` |
| `daily.py` | Theme rotation + generate pipeline |
| `gtm_render.py` | Center-safe GTM PNG |
| `xai_chat.py` | Chat completions + usage → costs |
| `xai_image.py` | Imagine API + cost events |
| `costs.py` | `xai_costs.jsonl` / `.md` |
| `journal.py` | `wallpaper_journal.md` / index |
| `reject_restore.py` | reject / restore |
| `selector.py` | date / mtime / latest / random / file / **next** cycle |
| `core.py` | `run_daily`, `apply_image` |
| `state.py` | IST today, `.last_set.txt` (date + last image path) |
| `apod.py` / `pexels.py` | Secondary Curated sources |
| `windows_wallpaper.py` / `notify.py` | SPI + Explorer `CurrentWallpaperPath` + Input Experience dismiss + optional toast |
| `about.py` | CLI journal block + desktop thumbnail card (`--dialog`) |

### Entry points

| Entry | Behavior |
|-------|----------|
| `wallpaper.py` | Full CLI (`about` prints journal text; `--dialog` is the thumbnail card) |
| `wallpaper` (PATH) | After `pip install -e .` → `wallpaper = wallpaper:main` in `pyproject.toml` |
| `run_daily_generate.py` | Midnight: generate if missing + set |
| `run_rotator.py` | Logon/unlock: set only (smart skip); also clears a leftover overlay |
| `run_clear_overlay.py` | Every minute: hide a fullscreen Input Experience window; does not change the wallpaper |
| `install_tasks.ps1` | Midnight generate + logon set + overlay guard; actions use `pythonw.exe` |
| `install_desktop_menu.ps1` | HKCU desktop grouped section: Reject / New / Prev / Read / Next |
| `uninstall_desktop_menu.ps1` | Remove those shell verbs |

## 4. Theme contracts

### gtm

1. Pick focus bucket from `GTM_FOCUS_ROTATION` (date + force nudge).  
2. Grok chat returns JSON: company, segment?, industry, business_model, channels[].  
3. Hard rules: real brands only; conglomerates → one segment; no home-wallpaper product companies as subject.  
4. Hard-ban companies already in the GTM journal (all used until ~30 unique). Retry once on a hit.  
5. Render with `render_gtm_infographic` (center card ~18% side margins).  
6. No on-image meta (“GTM · 16:9”, disclaimers).

### literary

1. Pick literature + painter buckets (`LITERARY_FOCUS_ROTATION`, `LITERARY_PAINTER_ROTATION`).  
2. Grok chat returns book scene + **famous painter** + style notes (style only; not a canvas-subject mashup).  
3. Hard-ban books/painters already in the literary journal (all used until ~30 unique). Retry once on a hit.  
4. Grok Imagine 16:9; center subject; quieter edges for icons.  
5. **No cyberpunk by default** unless user explicitly asks.  
6. Cost: chat + image estimate.  
7. Imagine `content-moderated` currently fails the run (no retry; painting has one).

### painting

1. Pick art-history bucket (`PAINTING_FOCUS_ROTATION`).  
2. Grok chat returns famous painting + reimagine direction (medium/era/setting).  
3. Hard-ban original canvases/artists already in the painting journal. Retry once on a hit.  
4. Grok Imagine 16:9; center composition.  
5. **No cyberpunk by default** unless user explicitly asks.  
6. **Nudes:** keep the canvas; fully clothe every figure in `image_prompt` (pose/setting stay recognizable). **Gore** (beheading, surgery, massacre close-ups) → pick a different work.  
7. Imagine `content-moderated`: no file, no journal. Log `painting Imagine attempt: title / artist`, replan once, second Imagine.  
8. Cost: chat + image estimate (successful Imagine only in `xai_costs.jsonl`).

## 5. Selection (set path)

Non-recursive listing of `Grok_Daily/` then `Curated/` (not `archive/`, not `_rejected/` unless path is explicit):

1. Filename contains today’s `YYYY-MM-DD` → newest among matches  
2. Else newest by mtime  
3. Else secondary folder same logic  

CLI overrides: `--file`, `--latest` (Grok_Daily only), `--random` (Grok_Daily + Curated).

### Theme pick for `new` / `new --force`

| Case | Theme |
|------|--------|
| `new --theme X` | X |
| `new` first time today | Calendar: `theme_for_day` |
| `new --force` / desktop **New** after a creative gen today | `next_theme(last_creative_today)` e.g. gtm→literary→painting→gtm |
| `new --force` with no creative gen yet today | Calendar theme |

### next / prev cycle (library only)

1. Build sorted library from `Grok_Daily/` (optional `+ Curated` via `--include-curated`).  
2. Read current image from `.last_set.txt` line 2 (`read_last_image_path`).  
3. Advance by +1 (`next`) or −1 (`prev`); wrap around.  
4. `apply_image` (updates state).  

Does **not** call xAI or create new files — local cycle only.

### Desktop context menu

Registry (per-user, no admin):

```text
HKCU\Software\Classes\DesktopBackground\Shell\GrokWallpaper01Reject … 05Next
  Position=Top; SeparatorBefore on first; SeparatorAfter on last
```

Win11 compact desktop menu does not expand registry flyouts, so these are grouped
top-level items rather than a cascade.

Command form (prefers venv `wallpaper.exe` after editable install; Read uses pythonw, no cmd.exe):

```text
cmd /c "cd /d <project> && <wallpaper.exe|python wallpaper.py> reject|new --force|prev|next"
"<pythonw> <project>\wallpaper.py about --dialog"
```

Read card (`rotator/about.py`): paper-style tkinter window with Pillow
thumbnail + Title / Description / Detail. MessageBox is fallback only.
Wrapping Read in `cmd.exe /c` leaves an empty console until the card closes.

Appears on **right-click empty desktop background** (not on icons).

## 6. Scheduling

| Task | Trigger | Script |
|------|---------|--------|
| `GrokWallpaper-DailyMidnight` | 00:00 local | `run_daily_generate.py` |
| `GrokWallpaper-LogonUnlock` | logon + unlock | `run_rotator.py` |
| `GrokWallpaper-ClearOverlay` | every 1 min + logon | `run_clear_overlay.py` |

Interactive user principal required for SPI and for seeing the overlay window. All three actions run `pythonw.exe` so Task Scheduler does not open a console. App “today” remains `Asia/Kolkata`. The overlay guard does not change the wallpaper.

## 7. Secrets & pricing env

| Key | Use |
|-----|-----|
| `XAI_API_KEY` | Chat + images |
| `XAI_CHAT_MODEL` | Default e.g. `grok-4-1-fast-reasoning` |
| `XAI_IMAGE_MODEL` | Default e.g. `grok-imagine-image` |
| `NASA_API_KEY` | APOD (else DEMO_KEY) |
| `PEXELS_API_KEY` | Optional |
| `XAI_PRICE_CHAT_INPUT_PER_MTOK` | Cost estimate |
| `XAI_PRICE_CHAT_OUTPUT_PER_MTOK` | Cost estimate |
| `XAI_PRICE_IMAGE_USD` | Cost estimate per image |

## 8. Logs

| File | Content |
|------|---------|
| `logs/wallpaper_journal.md` | Per-event human descriptions |
| `logs/wallpaper_index.md` | Table scan |
| `logs/xai_costs.jsonl` | Machine events |
| `logs/xai_costs.md` | Human spend summary |
| `logs/rotator.log` | Runtime log |

## 9. Acceptance checks

1. `wallpaper.py --new` creates dated file + journal + set (with keys).  
2. Second `--new` same day skips without `--force`.  
3. `reject` archives + APOD set.  
4. `restore --file` sets and journals.  
5. `next` / `prev` cycle local library and set.  
6. Desktop menu registers Reject / New / Prev / Read / Next under `DesktopBackground\Shell`; Read is pythonw with no cmd.exe.  
7. `pip install -e .` exposes `wallpaper` console script.  
8. Midnight task path is generate-if-missing.  
9. Airplane mode: `set --file` / `next` still work.  
10. No Bing dependency.
