# ROADMAP — Grok Surprise Wallpaper Rotator

## Shipped (v2)

- [x] Local Grok_Daily primary + Curated secondary  
- [x] Date-in-filename selection + mtime fallback (Asia/Kolkata)  
- [x] ctypes `SystemParametersInfoW`  
- [x] `.last_set.txt` smart dedupe  
- [x] Task Scheduler: midnight **generate** + logon/unlock **set** + every-minute overlay guard  
- [x] `wallpaper.py` CLI (`new`, `set`, `next`, `prev`, `clear-overlay`, `reject`, `restore`, `costs`, `status`, `curated`)  
- [x] Three themes: **gtm** / **literary** / **painting**  
- [x] One image per IST day (+ `--force`)  
- [x] GTM: live Grok research + Pillow center-safe infographic (no meta chrome)  
- [x] GTM industry diversity buckets (B2B, D2C, marketplace, fintech, …)  
- [x] Literary + painting via chat plan + Grok Imagine  
- [x] Literary: famous **painter style only** (not painting-as-scene mashup)  
- [x] No cyberpunk by default on art themes  
- [x] Journal + index (`logs/wallpaper_journal.md`)  
- [x] xAI cost estimates (`logs/xai_costs.*`)  
- [x] Reject → `_rejected/` + NASA APOD  
- [x] Restore past / rejected images  
- [x] **Next / Previous** cycle + **desktop right-click menu** (`install_desktop_menu.ps1`)  
- [x] Desktop menu: **New** + **Reject today (NASA)** shell verbs  
- [x] `wallpaper` console_script via `pyproject.toml` (`pip install -e .`)  
- [x] `.env` for XAI / NASA / optional Pexels + price overrides  
- [x] Seed art archived under `Grok_Daily/archive/`  
- [x] Bing disable guidance in README  
- [x] SPI set also writes Explorer `CurrentWallpaperPath` (stale Bing → black desktop)  
- [x] Dismiss fullscreen Windows Input Experience overlay (after set, on logon skip, `wallpaper clear-overlay`)  
- [x] `GrokWallpaper-ClearOverlay` every minute via `run_clear_overlay.py`  
- [x] Scheduled tasks run `pythonw.exe` so no console flashes  
- [x] Painting: clothe famous nudes in Imagine prompts; skip gore; one moderation retry  
- [x] `wallpaper about --dialog` thumbnail card (pythonw, no cmd.exe)  

## Public portfolio move

Done. Live tree: `C:\Users\jobjo\Github\Wallpapers` (not inside OneDrive). Public remote: `Jcube101/grok-wallpaper` (`origin`). The deleted private repo `Jcube101/Wallpapers` must not be recreated or used as a remote. `C:\Users\jobjo\projects\Wallpapers` is gone; do not recreate it or copy anything back.

The public README shows the two samples. They are copies under `docs/` (`gtm-cloudflare.png`, `painting-milkmaid.jpg`), not files from `Grok_Daily/`.

- [x] 1. Delete the private GitHub repo. Leave the project in `C:\Users\jobjo\projects\Wallpapers`.
- [x] 2. Remove the three scheduled tasks and the desktop menu while they still point at that path.
- [x] 3. Move the folder into the GitHub directory. Windows could not rename the open folder, so the files were copied. Tasks, menu, and the desktop now use the new path.
- [x] 4. Recreate `.venv` there and run `pip install -e .`. A moved venv keeps the old path.
- [x] 5. Reinstall tasks and the desktop menu with the new `python.exe`. The installer uses `pythonw.exe` beside it.
- [x] 6. Delete the local `.git` and start a new repository, only after the folder is in the new place. Fresh `main`, no commits yet. The copied image history is not in this tree.
- [x] 7. Confirm what Git tracks. Commit code, tests, installers, `.env.example`, `config.json.example`, and docs. Keep `.gitkeep` only for `Grok_Daily/` and `Curated/`. Leave out `.env`, `config.json`, `.venv`, `logs/`, `.last_set.txt`, and every generated image, including `archive/` and `_rejected/`. Committed on public `main` with the portfolio frame.
- [x] 8. Make the docs usable by someone else. Keep IST, the three themes, no Bing, Pillow GTM maps, and Imagine for literary and painting. Replace the personal `projects\wallpapers` path in the README. Keep `AGENTS.md` as session notes, including the local-only image rule.
- [x] 9. Add a short portfolio frame: what the tool does, one GTM screenshot and one painting, under `docs/`, not in the daily library. MIT is already named in `pyproject.toml`. README shows both samples.
- [x] 10. Create the new public repo from that clean tree and push `main` once. Do not reuse the private remote. Public repo is `Jcube101/grok-wallpaper`.

If the GitHub folder is inside OneDrive, the repo can live there. `.venv` stays ignored so OneDrive does not sync the environment.

## Next (small, high value)

| Item | Notes |
|------|--------|
| Persist 14-day GTM industry memory beyond index titles | Reduce same-sector clusters further |
| Literary Imagine moderation retry (same as painting) | Replan once on `content-moderated` |
| Log failed Imagine calls in `xai_costs.jsonl` (`ok=false`) | API still bills; JSONL currently only records 200s |
| Optional Pillow 16:9 normalize for odd drops | Phone screenshots |
| Unsplash secondary curated | Optional alongside Pexels |
| Align cost rates with live xAI pricing page | Document check cadence |

## Later

| Item | Notes |
|------|--------|
| Multi-monitor policies | Per-display files |
| Tray app | New / reject / restore / next / costs |
| GTM HTML export | Shareable one-pager from same JSON |
| Auto-generate only on AC power | Laptop battery guard |

## Explicitly out of scope

| Idea | Why |
|------|-----|
| Bing Wallpaper | Contradicts product |
| Imagine-rendered GTM text maps | Unreadable labels |
| Mandatory cloud account | Offline-first set path |Lwt
| Deleting user art without archive | Prefer `_rejected/` / `archive/` |
