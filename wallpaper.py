#!/usr/bin/env python3
"""Grok Surprise Wallpaper — daily habit CLI (3 themes + NASA reject + restore).

Themes (rotate by IST date): gtm | literary | painting
  - gtm: Grok research → clean 16:9 corporate infographic
  - literary / painting: Grok plan + Grok Imagine

Examples:
  python wallpaper.py --new
  python wallpaper.py new --theme literary --force
  python wallpaper.py reject
  python wallpaper.py restore --list
  python wallpaper.py restore --date 2026-07-15
  python wallpaper.py restore --file Grok_Daily/_rejected/foo.jpg
  python wallpaper.py costs
  python wallpaper.py set --latest
  python wallpaper.py next
"""

from __future__ import annotations

import argparse
import logging
import sys
import textwrap
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rotator.config import PROJECT_ROOT, load_config
from rotator.core import apply_image, run_daily
from rotator.costs import total_spend
from rotator.daily import THEMES, generate_daily, theme_for_day
from rotator.logging_setup import setup_logging
from rotator.reject_restore import list_restorable, reject_today, restore_image
from rotator.selector import latest_image, next_image, random_image, resolve_file_arg
from rotator.state import (
    already_set_today,
    read_last_image_path,
    read_last_set,
    today_in_tz,
)


def _normalize_argv(argv: list[str] | None) -> list[str]:
    if argv is None:
        argv = sys.argv[1:]
    aliases = {
        "--new": "new",
        "--surprise": "new",
        "--create": "new",
        "create": "new",
        "surprise": "new",
    }
    out = [aliases.get(a, a) for a in argv]
    if not out or out[0].startswith("-"):
        if any(x in argv for x in ("--new", "--surprise", "--create")):
            out.insert(0, "new")
        elif not out:
            out = ["--help"]
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wallpaper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Daily wallpapers: GTM map · literary scene · painting reimagining.",
        epilog=textwrap.dedent(
            """\
            themes (auto-rotate by IST date):
              gtm        Grok research → 16:9 corporate channel infographic
              literary   Book climax / best moment (Grok Imagine)
              painting   Famous painting reimagined (Grok Imagine)

            one image per day (IST). Use --force to regenerate.
            dislike today → reject (NASA APOD + archive to Grok_Daily/_rejected/).
            restore past images with restore --file / --date.

            examples:
              python wallpaper.py --new
              python wallpaper.py new --theme gtm --force
              python wallpaper.py reject
              python wallpaper.py restore --list
              python wallpaper.py restore --date 2026-07-19
              python wallpaper.py costs
              python wallpaper.py set --latest
              python wallpaper.py next
              python wallpaper.py prev
              python wallpaper.py about
              python wallpaper.py clear-overlay
              python wallpaper.py about --dialog
            """
        ),
    )
    p.add_argument("-c", "--config", default=None, help="Path to config.json")
    p.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-c", "--config", default=None, help="Path to config.json")
    common.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    sub = p.add_subparsers(dest="command", metavar="COMMAND")

    p_new = sub.add_parser(
        "new",
        parents=[common],
        help="Generate today's themed wallpaper (1/day) and set it",
    )
    p_new.add_argument(
        "--theme",
        choices=THEMES,
        default=None,
        help="Override theme (default: rotate by IST date)",
    )
    p_new.add_argument(
        "--force",
        action="store_true",
        help=(
            "Generate even if today already has an image. "
            "Advances to the next theme (gtm→literary→painting) after today's last gen"
        ),
    )
    p_new.add_argument(
        "--no-set",
        action="store_true",
        help="Generate only; do not change desktop",
    )

    p_set = sub.add_parser(
        "set",
        parents=[common],
        help="Force-set wallpaper (smart pick, --file, --latest, --random)",
    )
    pick = p_set.add_mutually_exclusive_group()
    pick.add_argument("--file", "-f", metavar="PATH", default=None)
    pick.add_argument("--latest", action="store_true", help="Newest in Grok_Daily/")
    pick.add_argument("--random", action="store_true", help="Random Grok_Daily + Curated")
    p_set.add_argument("--dry-run", action="store_true")

    p_next = sub.add_parser(
        "next",
        parents=[common],
        help="Set next wallpaper in Grok_Daily (then Curated); wraps around",
    )
    p_next.add_argument(
        "--include-curated",
        action="store_true",
        help="Include Curated/ in the cycle (default: Grok_Daily only)",
    )
    p_next.add_argument("--dry-run", action="store_true")

    p_prev = sub.add_parser(
        "prev",
        parents=[common],
        help="Set previous wallpaper in the cycle (wraps around)",
    )
    p_prev.add_argument("--include-curated", action="store_true")
    p_prev.add_argument("--dry-run", action="store_true")

    sub.add_parser(
        "clear-overlay",
        parents=[common],
        help="Hide a fullscreen Windows Input Experience window covering the desktop",
    )

    p_about = sub.add_parser(
        "about",
        parents=[common],
        help="Show Title / Description / Detail for the currently set wallpaper",
    )
    p_about.add_argument(
        "--dialog",
        action="store_true",
        help="Open a thumbnail card with the journal text (used by the desktop menu)",
    )
    p_about.add_argument(
        "--toast",
        action="store_true",
        help="Also show a short Windows toast (title + description)",
    )

    p_rej = sub.add_parser(
        "reject",
        parents=[common],
        help="Dislike today: archive to _rejected/, set NASA APOD, journal",
    )

    p_res = sub.add_parser(
        "restore",
        parents=[common],
        help="Bring back a past image and set it",
    )
    p_res.add_argument("--list", action="store_true", help="List restorable files")
    p_res.add_argument("--file", "-f", default=None, help="Path to image")
    p_res.add_argument("--date", default=None, help="IST date YYYY-MM-DD from journal")

    sub.add_parser("costs", parents=[common], help="Show estimated xAI spend summary")
    sub.add_parser("status", parents=[common], help="Today, theme, keys, journal pointers")

    p_cur = sub.add_parser("curated", parents=[common], help="Download APOD/Pexels → Curated")
    p_cur.add_argument("--source", choices=("apod", "pexels"), default="apod")
    p_cur.add_argument("--count", type=int, default=1)
    p_cur.add_argument("--query", default="minimal landscape nature serene")
    p_cur.add_argument("--set-today", action="store_true")

    p_prompt = sub.add_parser("prompt", parents=[common], help="Print today's theme label")
    return p


def cmd_new(args, cfg) -> int:
    result = generate_daily(
        cfg,
        force=args.force,
        theme_override=args.theme,
        set_wallpaper=not args.no_set,
        project_root=PROJECT_ROOT,
    )
    print(result.message)
    if not result.success:
        # Desktop New is a console that vanishes on exit. A credits refusal,
        # a second content block, or a dead network has to stay on screen.
        from rotator.notify import alert_generation_failure

        alert_generation_failure(result.message)
        return 1

    # If already generated today (no --force), still re-apply that file so a
    # desktop-menu click does something visible after the user cycled away.
    if result.skipped and not args.no_set and not args.force:
        from rotator.journal import find_entry_file

        rel = find_entry_file(PROJECT_ROOT, today_in_tz(cfg.timezone).isoformat())
        if rel:
            path = Path(rel)
            if not path.is_file():
                path = cfg.grok_daily_dir / Path(rel).name
            if path.is_file():
                applied = apply_image(cfg, path)
                print(applied.message)
                print(
                    "(Already generated today — re-applied. "
                    "Desktop menu / --force regenerates a brand-new image.)"
                )
                return 0 if applied.success else 1

    return 0 if result.success else 1


def cmd_set(args, cfg) -> int:
    image = None
    if args.file:
        try:
            image = resolve_file_arg(
                args.file, base=PROJECT_ROOT, extensions=cfg.image_extensions
            )
        except (FileNotFoundError, ValueError) as e:
            print(e, file=sys.stderr)
            return 1
    elif args.latest:
        image = latest_image(cfg.grok_daily_dir, cfg.image_extensions)
        if image is None:
            print("No images in Grok_Daily/", file=sys.stderr)
            return 1
    elif args.random:
        image = random_image(
            [cfg.grok_daily_dir, cfg.curated_dir], cfg.image_extensions
        )
        if image is None:
            print("No images found", file=sys.stderr)
            return 1

    if image is not None:
        result = apply_image(cfg, image, dry_run=args.dry_run)
    else:
        result = run_daily(cfg, force=True, dry_run=args.dry_run)
    print(result.message)
    return 0 if result.success else 1


def _cycle_folders(cfg, include_curated: bool) -> list:
    folders = [cfg.grok_daily_dir]
    if include_curated:
        folders.append(cfg.curated_dir)
    return folders


def cmd_next(args, cfg) -> int:
    current = read_last_image_path(cfg.state_file)
    image = next_image(
        _cycle_folders(cfg, args.include_curated),
        cfg.image_extensions,
        current,
        step=1,
    )
    if image is None:
        print("No images to cycle. Add files to Grok_Daily/.", file=sys.stderr)
        return 1
    result = apply_image(cfg, image, dry_run=args.dry_run)
    print(result.message)
    return 0 if result.success else 1


def cmd_about(args, cfg) -> int:
    from rotator.about import (
        about_caption,
        format_about,
        resolve_current_about,
        show_about_dialog,
        show_about_toast,
    )

    image, rec = resolve_current_about(PROJECT_ROOT, cfg.state_file)
    text = format_about(rec, image)
    print(text)
    if image:
        print(f"\nFile\n{image}")
    if args.toast:
        show_about_toast(rec, image)
    if args.dialog:
        if not show_about_dialog(about_caption(rec), text, record=rec, image=image):
            return 1
    if image is None:
        return 1
    return 0


def cmd_clear_overlay(args, cfg) -> int:
    from rotator.windows_wallpaper import dismiss_blocking_input_overlay

    hidden = dismiss_blocking_input_overlay()
    if hidden:
        print(f"Hid {hidden} fullscreen Windows Input Experience window(s).")
    else:
        print("Desktop overlay not present.")
    return 0


def cmd_prev(args, cfg) -> int:
    current = read_last_image_path(cfg.state_file)
    image = next_image(
        _cycle_folders(cfg, args.include_curated),
        cfg.image_extensions,
        current,
        step=-1,
    )
    if image is None:
        print("No images to cycle. Add files to Grok_Daily/.", file=sys.stderr)
        return 1
    result = apply_image(cfg, image, dry_run=args.dry_run)
    print(result.message)
    return 0 if result.success else 1


def cmd_reject(args, cfg) -> int:
    ok, msg = reject_today(cfg, project_root=PROJECT_ROOT)
    print(msg)
    return 0 if ok else 1


def cmd_restore(args, cfg) -> int:
    if args.list:
        for p in list_restorable(cfg):
            print(p)
        return 0
    path = None
    if args.file:
        try:
            path = resolve_file_arg(args.file, base=PROJECT_ROOT, extensions=cfg.image_extensions)
        except (FileNotFoundError, ValueError) as e:
            # allow _rejected even if suffix check fails edge cases
            path = Path(args.file)
            if not path.is_file():
                path = PROJECT_ROOT / args.file
            if not path.is_file():
                print(e, file=sys.stderr)
                return 1
    ok, msg = restore_image(cfg, path=path, day=args.date, project_root=PROJECT_ROOT)
    print(msg)
    return 0 if ok else 1


def cmd_costs(args, cfg) -> int:
    total = total_spend(PROJECT_ROOT)
    md = PROJECT_ROOT / "logs" / "xai_costs.md"
    print(f"Estimated total xAI spend: ${total:.4f} USD")
    print(f"Detail log: {md}")
    if md.is_file():
        # print last 15 lines of summary
        lines = md.read_text(encoding="utf-8").splitlines()
        print("\n".join(lines[:25]))
    return 0


def cmd_status(args, cfg) -> int:
    import os

    from rotator.xai_chat import resolve_chat_model
    from rotator.xai_image import DEFAULT_MODEL, resolve_xai_api_key

    day = today_in_tz(cfg.timezone)
    last = read_last_set(cfg.state_file)
    xai = bool(resolve_xai_api_key())
    model_img = (os.environ.get("XAI_IMAGE_MODEL") or DEFAULT_MODEL).strip()
    print(f"Today ({cfg.timezone}): {day.isoformat()}")
    print(f"Today's theme:       {theme_for_day(day)}")
    print(f"Last set:            {last.isoformat() if last else '(never)'}")
    print(f"Already set today:   {already_set_today(cfg.state_file, cfg.timezone)}")
    print(f"XAI_API_KEY:         {'yes' if xai else 'no'}")
    print(f"XAI_CHAT_MODEL:      {resolve_chat_model()}")
    print(f"XAI_IMAGE_MODEL:     {model_img}")
    nasa = cfg.nasa_api_key or ""
    print(
        f"NASA_API_KEY:        "
        f"{'DEMO_KEY' if nasa == 'DEMO_KEY' else f'set ({len(nasa)} chars)'}"
    )
    print(f"Est. total xAI $:    ${total_spend(PROJECT_ROOT):.4f}")
    print(f"Journal:             {PROJECT_ROOT / 'logs' / 'wallpaper_journal.md'}")
    print(f"Cost log:            {PROJECT_ROOT / 'logs' / 'xai_costs.md'}")
    print("Daily habit:         wallpaper --new   (or: python wallpaper.py --new)")
    print("Cycle:               wallpaper next / prev")
    print("About current:       wallpaper about")
    print("Dislike today:       wallpaper reject")
    print("Restore:             wallpaper restore --list")
    print("Desktop menu:        .\\install_desktop_menu.ps1")
    return 0


def cmd_curated(args, cfg) -> int:
    dest = cfg.apod_save_to or cfg.curated_dir
    if args.source == "apod":
        from rotator.apod import fetch_apod

        paths = fetch_apod(api_key=cfg.nasa_api_key, count=args.count, dest_dir=dest)
    else:
        from rotator.pexels import fetch_pexels

        paths = fetch_pexels(
            cfg.pexels_api_key, query=args.query, count=args.count, dest_dir=dest
        )
    if not paths:
        print(f"No images from {args.source}")
        return 1
    for p in paths:
        print(f"Saved: {p}")
    if args.set_today:
        r = run_daily(cfg, force=True)
        print(r.message)
        return 0 if r.success else 1
    return 0


def cmd_prompt(args, cfg) -> int:
    day = today_in_tz(cfg.timezone)
    t = theme_for_day(day)
    print(f"Today {day.isoformat()} → theme: {t}")
    print("Run: python wallpaper.py --new")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = _normalize_argv(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2

    cfg = load_config(args.config)
    setup_logging(cfg.log_file, level=logging.DEBUG if args.verbose else logging.INFO)

    dispatch = {
        "new": cmd_new,
        "set": cmd_set,
        "next": cmd_next,
        "prev": cmd_prev,
        "clear-overlay": cmd_clear_overlay,
        "about": cmd_about,
        "reject": cmd_reject,
        "restore": cmd_restore,
        "costs": cmd_costs,
        "status": cmd_status,
        "curated": cmd_curated,
        "prompt": cmd_prompt,
    }
    fn = dispatch.get(args.command)
    if not fn:
        parser.print_help()
        return 2
    return fn(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
