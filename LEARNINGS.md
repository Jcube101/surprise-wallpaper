# LEARNINGS — Grok Surprise Wallpaper Rotator

## 1. “Daily wallpaper” ≠ “daily generate”

Early design only **set** existing files. Users expected new files every midnight.

**Learning:** Document the split clearly, then wire midnight to **`run_daily_generate.py`** while logon stays set-only (cheap, safe).

## 2. One image per day needs a journal, not just files

Filenames alone don’t answer “what was day-before-yesterday about?”

**Learning:** Append-only `wallpaper_journal.md` + index. Status `active` / `rejected` / `restored` drives the one-per-day guard.

## 3. GTM belongs in code, not Imagine

Channel maps need correct, readable labels. Image models garble text and invent structure.

**Learning:** Grok for **research JSON**; **Pillow** for the 16:9 infographic. Literary/painting stay on Imagine.

## 4. Prompt contamination is real

Asking for a “**wallpaper** GTM channel map” made the model pick wallpaper brands (Lick) and design tools (Canva).

**Learning:** Say “desktop learning infographic” / “GTM map for operators.” Explicitly ban wallpaper/home-decor product companies as **subjects**. Rotate industry **focus buckets**.

## 5. Desktop icons need a safe zone

Edge-heavy layouts fight the user’s icon columns.

**Learning:** Center content card (~18% side margins). Ask Imagine for center-weighted composition on art themes. Drop footer meta so cards can use full height.

## 6. Reject needs a real escape hatch

“Generate again” isn’t enough when the user wants out of a theme for the day.

**Learning:** `reject` → `_rejected/` + NASA APOD + journal. Preserve art; don’t delete.

## 7. Costs must be visible

xAI chat + image adds up quietly.

**Learning:** Log every call to JSONL + markdown summary with **editable price env vars**. Journal carries per-run estimate.

## 8. Task Scheduler Python path

`$PWD\.venv\Scripts\python.exe` fails if venv was never created.

**Learning:** Create venv in setup docs; `install_tasks.ps1` must receive a path that `Test-Path` accepts. Prefer venv so Pillow is available at midnight.

## 9. Bing will steal the desktop

Rotator success ≠ Bing off. Uninstall is also not enough: Explorer keeps
`HKCU\…\Explorer\Wallpapers\CurrentWallpaperPath`. After Bing Wallpaper is
gone that path can still point at a **deleted** file; SPI’s
`Control Panel\Desktop\WallPaper` looks fine while the shell paints **black**
(background color `0 0 0`).

**Learning:** Uninstall Bing + Background = Picture, **and** every set must
overwrite `CurrentWallpaperPath` / `BackgroundType=0` in
`windows_wallpaper.set_wallpaper`. `wallpaper set --latest` recovers a black
desktop when the icons and right-click still work.

A fullscreen `TextInputHost` (“Windows Input Experience”) window is a different
failure: it paints nothing and eats clicks, so icons and the desktop menu
vanish while the wallpaper file is fine. `set_wallpaper` hides that window
(and stops `TextInputHost` only if hide does not stick). The logon/unlock skip
path does the same. `GrokWallpaper-ClearOverlay` runs `run_clear_overlay.py`
every minute so a leftover window cannot sit there until the next unlock.
`wallpaper clear-overlay` is the manual command.

## 10. Archive old seeds

Mixing dated seed fantasy packs with the new three-theme system confuses `--latest` and mental model.

**Learning:** Move pre-format art to `Grok_Daily/archive/` (non-recursive selector ignores subfolders).

## 11. Spoilers are a feature for this product

Literary climaxes are the point; journal text should name the moment.

**Learning:** Don’t water down literary descriptions for spoiler-safety unless the user asks.

## 12. Cyberpunk is a default trap for “reimagine”

Open-ended painting reimaginings repeatedly collapsed to neon megacity cyberpunk (Starry Night, Persistence of Memory).

**Learning:** Ban cyberpunk in system + user + image suffix unless the user explicitly requests it. Prefer period, medium, season, or quiet modern shifts.

## 13. Literary needs style direction, not only a scene

A bare “Room 101” Imagine prompt looked flat; users want a **famous painter’s style** applied to the literary subject — not a mashup that replaces the scene with a known canvas.

**Learning:** Pick painter + style notes in the plan JSON; keep book characters/setting; ban “reimagine painting X as book Y” confusion.

## 14. Desktop right-click is a real UX win for “next”

People expect to flip wallpapers without opening a terminal. Windows exposes **DesktopBackground** shell verbs under HKCU (no admin).

**Learning:** `next`/`prev` cycle a sorted local library from `.last_set.txt` path; register menu via `install_desktop_menu.ps1` with `cd` to project so config/`.env` resolve. Document: click **empty background**, not icons; restart Explorer if verbs missing. Also expose **New** and **Reject** as shell verbs; warn that New is slow/network. Prefer `wallpaper` console script (`pip install -e .`) so menu commands match CLI.

## 15. Soft “avoid recent titles” does not stop celebrity canon

Literary/painting plans only saw the last 12 *mixed* index titles (mostly GTM) at
temperature 0.5. Models collapsed onto Moby-Dick/Ahab, Dorian Gray, Starry Night,
The Kiss, Rembrandt, and Turner — including the same climax with a new painter.
GTM had the same hole: last-20 mixed titles dropped Lemonade/Teladoc/Tesla/
Robinhood, so those companies came back.

**Learning:** Ban companies/books/canvases/painters from the *theme’s* journal
(all used until ~30 unique, then a rolling window). Rotate focus buckets.
Retry once on a ban hit. Higher temperature for art plans than for GTM JSON.

## 16. Console script keeps PATH and menu in sync

Dual entry (`python wallpaper.py` vs installed `wallpaper`) confuses Task Scheduler and menus.

**Learning:** Declare `wallpaper = "wallpaper:main"` in `pyproject.toml`; editable install puts `wallpaper.exe` next to venv python; menu installer prefers that exe when present.

## 17. Imagine moderation never produces a file

`imagine:content-moderated` is HTTP 400 **before** bytes. Nothing lands in
`Grok_Daily/`, the journal is not appended, `.last_set.txt` is not updated,
midnight `run_daily_generate.py` exits 1 (no APOD fallback). Chat plan cost is
logged; the failed Imagine call is not (the API still billed).

Italian Renaissance / Olympia / Venus buckets look like “the model failed.”
It generated a nude. Skipping Botticelli is the wrong fix — this product already
reimagines.

**Learning:** Keep famous nudes; **clothe every figure** in `image_prompt`
(same pose, grouping, setting). Skip **gore** (Judith, Gross Clinic, Anatomy
Lesson corpse) and retry a different canvas. Log
`painting Imagine attempt: Title / Artist` before the API call. Painting
replans + second Imagine once on moderation; literary does not yet.

## 18. Desktop Read cannot go through cmd.exe

`cmd /c … && pythonw about --dialog` keeps an **empty console** open for the
life of the dialog. Win32 `MessageBox` is the 1995 info alert — no image, no
wrapping.

**Learning:** Register Read as `"pythonw.exe" "…\wallpaper.py" about --dialog"`
(absolute paths, no cmd). Show a stdlib tkinter paper card with a Pillow
thumbnail + Title / Description / Detail. CLI `wallpaper about` stays plain
text. MessageBox remains the fallback if tkinter cannot start.

## 19. Task Scheduler + python.exe flashes a console

`python.exe` is a console program. `GrokWallpaper-ClearOverlay` runs every
minute, so pointing that task at `python.exe` opens a terminal titled with
`run_clear_overlay.py` and closes it when the check ends. Midnight and unlock
do the same, less often.

**Learning:** `install_tasks.ps1` still takes a `python.exe` path (so
`Test-Path` and the venv check stay the same) and registers every task with
the `pythonw.exe` beside it. The guard logs to `logs/rotator.log` only when it
actually hides a window. Re-run the installer if a console starts flashing again.
