# Grok Surprise Wallpaper Rotator

Daily **desktop learning + art** for Windows — **one image per IST day**, three rotating themes, local-first, **no Bing**.

| Theme (by date) | What you get | How |
|-----------------|--------------|-----|
| **gtm** | Center-safe **16:9 corporate** GTM channel map | Grok chat research → Pillow render |
| **literary** | Book climax / best scene | Grok plan → **Grok Imagine** |
| **painting** | Famous painting reimagined | Grok plan → **Grok Imagine** |

| Also | Location |
|------|----------|
| Journal (what each day was) | `logs/wallpaper_journal.md` |
| Quick index | `logs/wallpaper_index.md` |
| xAI cost estimates | `logs/xai_costs.md` · `python wallpaper.py costs` |
| Rejected images | `Grok_Daily/_rejected/` |
| Older seed art | `Grok_Daily/archive/` |

“Today” = **`Asia/Kolkata` (IST)** for selection, journal, and one-image-per-day.

## Samples

Two copies live in [`docs/`](docs/portfolio.md). The daily library stays on the machine.

**GTM.** Cloudflare, 22 October 2026. Pillow center card from live research.

![Cloudflare go-to-market map](docs/gtm-cloudflare.png)

**Painting.** Vermeer’s *The Milkmaid*, reimagined as an autumn watercolor, 18 October 2026.

![The Milkmaid reimagined as an autumn watercolor](docs/painting-milkmaid.jpg)

---

## Quick start

```powershell
cd path\to\Wallpapers
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .                       # installs deps + `wallpaper` on PATH (venv)
# or: pip install -r requirements.txt  # deps only; use python wallpaper.py …
copy config.json.example config.json   # if needed
# ensure .env has XAI_API_KEY, XAI_CHAT_MODEL, XAI_IMAGE_MODEL, NASA_API_KEY

wallpaper status
wallpaper --new                        # generate today's theme + set desktop
# still works: python wallpaper.py --new
```

**See it change:** desktop updates; journal gets a new entry; costs log updates for xAI calls.

Activate the venv in new shells so `wallpaper` resolves:

```powershell
.\.venv\Scripts\Activate.ps1
wallpaper next
```

---

## Daily workflow

### Automatic vs manual

| Piece | Midnight task | Logon / unlock | You |
|-------|---------------|----------------|-----|
| **Generate** today’s theme | **Yes** (`run_daily_generate.py`) | No | `python wallpaper.py --new` |
| **Set** desktop | After generate | Set only if not already today | `set` / `restore` / `next` / `prev` |
| **Cycle library** | No | No | `next` / `prev` or desktop right-click menu |
| **Reject → NASA** | No | No | `python wallpaper.py reject` |
| **Clear blank overlay** | After set | On skip | `wallpaper clear-overlay` (also every minute) |

Register / refresh tasks (use **venv** Python if you have one):

```powershell
.\install_tasks.ps1 -PythonPath "$PWD\.venv\Scripts\python.exe"
# or system Python:
# .\install_tasks.ps1 -PythonPath "C:\Users\...\Python311\python.exe"
```

Pass `python.exe`. The installer runs all three tasks with `pythonw.exe` beside that interpreter, so no console window flashes. Tasks: `GrokWallpaper-DailyMidnight`, `GrokWallpaper-LogonUnlock`, `GrokWallpaper-ClearOverlay` (every minute; hides a blank Input Experience window only).

### One image per day

- Default: skip generate if journal already has an **active** entry for today.  
- Extra image today (next theme): `wallpaper new --force` or desktop **New**  
  (gtm → literary → painting → … after today’s last creative gen)  
- Theme override: `wallpaper new --theme gtm|literary|painting`

### Dislike today’s image → NASA

```powershell
python wallpaper.py reject
```

1. Moves today’s file to `Grok_Daily/_rejected/`  
2. Downloads NASA APOD → `Curated/`  
3. Sets APOD + journal note  

### Restore a past image

```powershell
python wallpaper.py restore --list
python wallpaper.py restore --file Grok_Daily\2026-07-19_gtm_etsy_sellers.png
python wallpaper.py restore --date 2026-07-19
python wallpaper.py restore --file Grok_Daily\_rejected\some.jpg
```

### Costs

```powershell
python wallpaper.py costs
```

Estimates use `XAI_PRICE_*` env defaults (adjust to your xAI plan). See `logs/xai_costs.md`.

---

## CLI reference

```powershell
wallpaper --help
# or: python wallpaper.py --help
```

| Command | Action |
|---------|--------|
| `new` / `--new` | First gen of day = calendar theme + set |
| `new --theme …` | Force a specific theme |
| `new --force` | Next theme after today’s last creative gen |
| `new --no-set` | Generate only |
| `set` | Force daily selector |
| `set --file PATH` | Exact file (relative to project root) |
| `set --latest` | Newest in `Grok_Daily/` (not archive) |
| `set --random` | Random Grok_Daily + Curated |
| `set --dry-run` | Show pick only |
| `next` / `prev` | Cycle library (Grok_Daily; wrap around) |
| `about` | Title / Description / Detail for the current wallpaper (`--dialog` for a thumbnail card) |
| `clear-overlay` | Hide a fullscreen Windows Input Experience window covering the desktop |
| `reject` | Archive today → NASA APOD |
| `restore` | Bring back past / rejected image |
| `costs` | Estimated xAI spend |
| `status` | Theme, keys, journal paths |
| `curated --source apod\|pexels` | Fill Curated |
| `prompt` | Print today’s theme label |

Legacy and task entry points: `run_rotator.py` (set only), `run_daily_generate.py` (midnight), `run_clear_overlay.py` (overlay guard), `set_today.py`, `download_apod.py`.

### Right-click desktop menu

```powershell
pip install -e .   # so wallpaper.exe exists in .venv\Scripts
.\install_desktop_menu.ps1 -PythonPath "$PWD\.venv\Scripts\python.exe"
```

**Right-click the desktop background** (empty area, not an icon). The five items sit together at the top of the menu:

| Menu item | Command |
|-----------|---------|
| **Reject today (NASA APOD)** | `wallpaper reject` |
| **New Grok wallpaper** | `wallpaper new --force` — next theme in cycle if today already has one (gtm→literary→painting; 30–90s, xAI) |
| **Previous Grok wallpaper** | `wallpaper prev` |
| **Read about this wallpaper** | `wallpaper about --dialog` — thumbnail card with Title, Description, Detail |
| **Next Grok wallpaper** | `wallpaper next` |

Remove: `.\uninstall_desktop_menu.ps1`  
If items don’t show: restart Explorer (Task Manager → Windows Explorer → Restart) or sign out/in.

---

## GTM rules (learning wallpapers)

- **Live research** via xAI chat (`XAI_CHAT_MODEL`) — not a fixed company list.  
- **Simple companies:** full channel mix (inbound, outbound, partner, sales, events, PLG, …).  
- **Conglomerates:** **one segment only** (e.g. AWS, Prime Video, Etsy sellers).  
- **Variety:** daily focus buckets rotate B2B SaaS, D2C, marketplace, fintech, media, etc.  
- **Not** wallpaper/home-decor brands as the subject (even though this app sets wallpapers).  
- **Layout:** content in the **center** (edge margins for desktop icons).  
- **No meta chrome** on the image (no “GTM · 16:9” / disclaimer footer).  
- **Readable text** via Pillow — not Grok Imagine.

Literary **spoilers are intentional** in the journal.

**Style:** literary/painting avoid **cyberpunk** unless you ask for it (prefer painterly / classical / natural / quiet modern).

**Painting nudes:** the reimagining keeps the famous composition but **clothes every figure** so Imagine does not reject the image. Graphic violence (beheadings, surgery) is skipped for a different canvas; one automatic retry if Imagine still returns `content-moderated`. A failed Imagine call does **not** leave a file in `Grok_Daily/` — nothing is saved until the image is accepted.

---

## Config & secrets

### `config.json`

Paths, timezone (`Asia/Kolkata`), toast, image extensions. Copy from `config.json.example`.

### `.env` (do not commit)

```text
XAI_API_KEY=...
XAI_CHAT_MODEL=grok-4-1-fast-reasoning    # or your Grok 4.x id
XAI_IMAGE_MODEL=grok-imagine-image
NASA_API_KEY=...
# optional: PEXELS_API_KEY, XAI_PRICE_CHAT_*_PER_MTOK, XAI_PRICE_IMAGE_USD
```

See `.env.example`.

### Dependencies

```text
pip install -r requirements.txt
# windows-toasts, tzdata, Pillow
```

---

## Disable Bing Wallpaper (required)

This rotator only changes the desktop when **it** runs. **Bing Wallpaper** or **Windows Spotlight** will overwrite it. Uninstalling Bing is not enough if Explorer still points at a deleted Bing file (`CurrentWallpaperPath`) — that paints a **black desktop**.

1. **Settings → Apps → Installed apps** → uninstall **Bing Wallpaper**  
2. **Settings → Personalization → Background** → **Picture** (not Windows Spotlight)  
3. Re-apply: `wallpaper set --latest` (also overwrites Explorer’s wallpaper path)  
4. Confirm tasks in `taskschd.msc`: `GrokWallpaper-DailyMidnight`, `GrokWallpaper-LogonUnlock`, `GrokWallpaper-ClearOverlay`

Details in [Troubleshooting](#troubleshooting).

---

## Folder layout

```text
wallpapers/
  wallpaper.py              # main CLI
  run_daily_generate.py     # midnight: generate if missing + set
  run_rotator.py            # logon: set only
  run_clear_overlay.py      # every minute: hide a blank Input Experience window
  install_tasks.ps1         # registers the three tasks (they run via pythonw.exe)
  uninstall_tasks.ps1
  pyproject.toml            # pip install -e . → `wallpaper` CLI
  install_desktop_menu.ps1  # grouped: Reject / New / Prev / Read / Next
  uninstall_desktop_menu.ps1
  config.json.example
  .env.example
  Grok_Daily/               # primary images (dated YYYY-MM-DD_*; local, not in git)
    archive/                # older seed pack (no date prefix)
    _rejected/              # disliked generations
  Curated/                  # NASA APOD / Pexels (local, not in git)
  logs/                     # journal, index, costs, rotator.log
  rotator/                  # Python package
  docs/                     # public samples only (not the daily library)
    portfolio.md
    gtm-cloudflare.png
    painting-milkmaid.jpg
  README.md SPEC.md ROADMAP.md LEARNINGS.md AGENTS.md LICENSE
```

---

## Project docs

| Doc | Contents |
|-----|----------|
| [SPEC.md](SPEC.md) | Architecture & contracts |
| [ROADMAP.md](ROADMAP.md) | Done / next |
| [LEARNINGS.md](LEARNINGS.md) | Design lessons |
| [AGENTS.md](AGENTS.md) | Instructions for future AI sessions |
| [docs/portfolio.md](docs/portfolio.md) | What the tool does, with the two public samples |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Config not found | `copy config.json.example config.json` |
| `install_tasks` Python not found | Create venv first, or pass real `python.exe` path |
| `new` needs API | Set `XAI_API_KEY` in `.env` |
| Pillow / GTM fails | `pip install Pillow` (in venv) |
| Already generated today | `new --force` (next theme) or `reject` |
| Desktop reverts to Bing | Uninstall Bing Wallpaper; Background = Picture |
| Black desktop, icons and right-click still work | Stale Bing `CurrentWallpaperPath`; `wallpaper set --latest` |
| Blank desktop, no icons, right-click does nothing | Fullscreen Windows Input Experience window. Cleared after each set, on logon/unlock, and every minute by `GrokWallpaper-ClearOverlay`. Immediate: `wallpaper clear-overlay` |
| A terminal flashes a wallpaper script every minute | Re-run `.\install_tasks.ps1`. Tasks must use `pythonw.exe`, not `python.exe` |
| `new` fails `content-moderated` | No file was saved. Rerun `wallpaper --new`. Painting clothes nudes and retries once |
| Read about flashes an empty console | Re-run `.\install_desktop_menu.ps1` (Read must be pythonw, not `cmd /c`) |
| Wrong industry cluster on GTM | Improved diversity buckets; `new --theme gtm --force` |
| Restore archive image | `set --file Grok_Daily\archive\name.jpg` |

---

## Philosophy

1. **One useful image a day** — learn GTM, feel literature, see art.  
2. **Readable GTM** via code render; **scenes** via Imagine.  
3. **Journal + costs** so days are explainable and spend is visible.  
4. **Reject → NASA** when the day misses.  
5. **No Bing.** Offline **set** still works from local files.
