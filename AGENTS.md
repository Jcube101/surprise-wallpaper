# AGENTS.md — Instructions for future AI sessions

## Mission

One **themed** desktop wallpaper per **Asia/Kolkata** day:

| Theme | Delivery |
|-------|----------|
| **gtm** | Grok chat research → center-safe Pillow GTM map (no meta text) |
| **literary** | Grok plan + Grok Imagine (center subject; journal may spoil) |
| **painting** | Grok plan + Grok Imagine (center subject) |

Secondary: NASA APOD on **reject**. Journal + xAI cost logs. **No Bing.**

## Repo map

```text
pyproject.toml               # pip install -e . → wallpaper console script
wallpaper.py                 # CLI module (entry: wallpaper:main)
run_daily_generate.py        # midnight generate-if-missing + set
run_rotator.py               # logon set-only
run_clear_overlay.py         # every minute: hide a blank Input Experience window
install_desktop_menu.ps1     # desktop: Reject / New / Prev / Read / Next (grouped)
uninstall_desktop_menu.ps1
rotator/daily.py             # pipeline + GTM diversity + painter-style literary
rotator/gtm_render.py        # Pillow 16:9 center card
rotator/about.py             # CLI text + desktop thumbnail card
rotator/windows_wallpaper.py # SPI + CurrentWallpaperPath + overlay dismiss
rotator/selector.py          # includes next_image cycle
rotator/state.py             # date + last image path
rotator/journal.py / costs.py
rotator/reject_restore.py
Grok_Daily/                  # dated primaries (local; not in git)
  archive/                   # old seeds (no auto-select)
  _rejected/                 # disliked gens
Curated/                     # APOD / Pexels (local; not in git)
logs/                        # journal, costs, rotator.log
prompts/                     # legacy tasteful templates (historical)
docs/                        # public samples only (not the daily library)
```

## Hard rules

1. Do not reintroduce Bing or Imagine-based GTM text maps.  
2. Do not put meta chrome on GTM images (`GTM · 16:9`, disclaimers).  
3. Keep GTM content **center-safe** for desktop icons.  
4. GTM subjects: real companies; conglomerates → one segment; **not** wallpaper/home-decor brands.  
5. First gen of day uses calendar theme; **`--force` / desktop New** advances to the **next** theme after today's last creative gen (not a redo of the same theme).  
6. Never commit `.env`, API keys, or the daily wallpaper libraries. `Grok_Daily/` and `Curated/` stay local; git keeps only each folder's `.gitkeep`. The two files in `docs/` are the public samples.  
7. Extend modules; don’t rewrite architecture casually.  
8. **No cyberpunk by default** (neon megacity, holographic rain, acid noir, etc.) on literary/painting — only if the user explicitly asks. Prefer painterly, classical, natural light, historical, quiet modern.  
9. **Literary images:** apply a **famous painter's style only** (brushwork/palette/light). Do **not** reimagine a famous painting *as* the literary climax — the book scene stays the subject.  
10. **Painting nudes:** keep the famous canvas; **fully clothe** every figure in the Imagine prompt (pose/setting stay recognizable). Skip gore (beheading, surgery, massacre close-ups) and retry a different work.  
11. After SPI, always write Explorer `CurrentWallpaperPath` so a leftover Bing file cannot paint a black desktop.  
12. A fullscreen **Windows Input Experience** window (`TextInputHost`) blanks the desktop and eats right-clicks. Dismiss it after every set, on the logon/unlock skip path, and from `GrokWallpaper-ClearOverlay` (`run_clear_overlay.py`, every minute). Do not drop that task.  
13. Scheduled tasks run **`pythonw.exe`** beside the `python.exe` passed to `install_tasks.ps1`. Do not point Task Scheduler at `python.exe` — the every-minute guard would flash a console.  

## User commands (prefer these)

```powershell
# Prefer console script after: pip install -e .
wallpaper --new
wallpaper new --theme gtm --force
wallpaper next
wallpaper prev
wallpaper about
wallpaper clear-overlay
wallpaper reject
wallpaper restore --list
wallpaper costs
wallpaper status
# still valid: python wallpaper.py …

.\install_desktop_menu.ps1   # grouped: Reject / New / Prev / Read / Next
```

## When user says “Surprise me” / “new wallpaper”

1. Run or guide `python wallpaper.py --new` (or `--theme` / `--force` as asked).  
2. Confirm journal entry + desktop set.  
3. If they dislike: `reject` (NASA).  
4. Point them to `logs/wallpaper_journal.md` for descriptions.  

## Editing GTM / literary / painting research

See `GTM_FOCUS_ROTATION`, `LITERARY_FOCUS_ROTATION`, `LITERARY_PAINTER_ROTATION`,
`PAINTING_FOCUS_ROTATION` in `rotator/daily.py`.

Diversity = focus buckets + **theme-specific** journal bans (GTM companies /
books / original canvases / painters), not mixed last-N index titles. Soft
“Avoid recent:” is not enough — models collapse onto Lemonade/Teladoc/Tesla,
Moby-Dick, Dorian Gray, Starry Night, The Kiss, Rembrandt, Turner. Retry the
plan once if it hits a ban.

Imagine `content-moderated` never writes a file or journal entry (desktop
unchanged). Painting: clothe nudes; on moderation log the title, replan once,
second Imagine. Literary does the same one Imagine retry with a quieter scene.
If that second image is moderated too, show the content-moderation dialog.
A credits refusal or a failure to reach xAI shows its own dialog. Failed
Imagine costs are not in `xai_costs.jsonl` (chat plan still is).

## Secrets

`.env`: `XAI_API_KEY`, `XAI_CHAT_MODEL`, `XAI_IMAGE_MODEL`, `NASA_API_KEY`, optional `XAI_PRICE_*`, `PEXELS_API_KEY`.

## Desktop menu

- Install: `.\install_desktop_menu.ps1 -PythonPath "$PWD\.venv\Scripts\python.exe"`  
- Five top-level verbs (Win11 compact menu does not expand registry flyouts):  
  `GrokWallpaper01Reject` … `05Next`, `Position=Top`, separators around the group  
- Order: Reject, New, Previous, **Read about this wallpaper**, Next  
- Read → `pythonw wallpaper.py about --dialog` (tkinter thumbnail card; **no** `cmd.exe`)  
- Prefer `wallpaper.exe` from venv when present; wrapping Read in `cmd /c` leaves an empty console until the card closes  
- User must right-click **empty desktop**, not an icon.  
- `next`/`prev`/`about`/`clear-overlay` are local only; `new`/`reject` may hit network  

## Scheduled tasks

`.\install_tasks.ps1 -PythonPath "$PWD\.venv\Scripts\python.exe"` registers three interactive tasks. The script you pass is `python.exe`; the tasks execute `pythonw.exe` next to it.

| Task | When | Script |
|------|------|--------|
| `GrokWallpaper-DailyMidnight` | 00:00 local | `run_daily_generate.py` |
| `GrokWallpaper-LogonUnlock` | logon + unlock | `run_rotator.py` (set only; also clears a leftover overlay) |
| `GrokWallpaper-ClearOverlay` | every minute + logon | `run_clear_overlay.py` (overlay only; does not change the wallpaper) |  

## Verification

```powershell
pip install -e .
wallpaper status
wallpaper clear-overlay
wallpaper next --dry-run
wallpaper prev --dry-run
wallpaper new --force --no-set   # careful: costs $
```

## Voice

Concise, technical, clear. Emphasize **one command**, **journal**, **costs**, **next/prev**, and **visible desktop change**.
