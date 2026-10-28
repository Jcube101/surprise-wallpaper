# prompts/ — Historical & optional templates

The **live** daily system no longer depends on freeform tasteful fantasy templates.

| Live path | Where |
|-----------|--------|
| GTM / literary / painting | `rotator/daily.py` (+ `gtm_render.py`, xAI chat/image) |
| Journal | `logs/wallpaper_journal.md` |
| Costs | `logs/xai_costs.md` |

## Files here

| File | Status |
|------|--------|
| `TEMPLATES.md` | Legacy tasteful + fantastical prompt library (optional reference) |
| `USED_BATCH_*.md` | Local only. Gitignored. Exact prompts from the July 2026 seed packs. |

## Daily habit (current)

```powershell
pip install -e .              # once per venv → `wallpaper` on PATH
wallpaper --new
wallpaper next                # or right-click desktop
wallpaper reject              # dislike today → NASA
wallpaper costs
```

Desktop menu (grouped: Reject / New / Prev / Read / Next): `.\install_desktop_menu.ps1` (see root README).

Open `logs/wallpaper_journal.md` for what each day depicted.
