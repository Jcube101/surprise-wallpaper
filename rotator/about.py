"""Show Title / Description / Detail for the currently set wallpaper."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from rotator.journal import JournalRecord, find_record_for_path
from rotator.state import read_last_image_path

log = logging.getLogger(__name__)

_THUMB_W = 472
_THUMB_H = 266
_BG = "#f3eee4"
_INK = "#1f1a14"
_MUTED = "#6f675e"
_RULE = "#d9d0c4"
_BTN_BG = "#2a2420"
_BTN_FG = "#f3eee4"


@dataclass(frozen=True)
class AboutView:
    caption: str
    kicker: str
    title: str
    description: str
    detail: str
    image: Path | None


def about_view(record: JournalRecord | None, image: Path | None) -> AboutView:
    """Structured fields for the CLI block and the desktop card."""
    if record and record.theme and record.day:
        kicker = f"{record.theme}  ·  {record.day}"
    elif image:
        kicker = image.name
    else:
        kicker = "Wallpaper"
    title = (record.title if record else "") or (image.name if image else "(unknown)")
    description = (record.description if record else "") or (
        "No journal entry for this file." if image else "No wallpaper is set yet."
    )
    detail = (record.detail if record else "") or "—"
    return AboutView(
        caption=about_caption(record),
        kicker=kicker,
        title=title,
        description=description,
        detail=detail,
        image=image if image and image.is_file() else None,
    )


def format_about(record: JournalRecord | None, image: Path | None) -> str:
    """Plain-text block matching the journal fields, for CLI or a dialog."""
    view = about_view(record, image)
    return (
        f"Title\n{view.title}\n\n"
        f"Description\n{view.description}\n\n"
        f"Detail\n{view.detail}"
    )


def about_caption(record: JournalRecord | None) -> str:
    if record and record.theme and record.day:
        return f"Wallpaper · {record.theme} · {record.day}"
    return "Wallpaper"


def resolve_current_about(
    project_root: Path, state_file: Path
) -> tuple[Path | None, JournalRecord | None]:
    image = read_last_image_path(state_file)
    rec = find_record_for_path(project_root, image) if image else None
    return image, rec


def show_about_dialog(
    caption: str,
    body: str,
    *,
    record: JournalRecord | None = None,
    image: Path | None = None,
) -> bool:
    """Desktop card (thumbnail + journal). Falls back to a MessageBox."""
    view = about_view(record, image)
    if _show_about_card(view):
        return True
    return _show_message_box(caption or view.caption, body)


def _show_about_card(view: AboutView) -> bool:
    try:
        import tkinter as tk
    except ImportError as e:
        log.warning("tkinter unavailable for about card: %s", e)
        return False

    try:
        _enable_dpi_awareness()
        root = tk.Tk()
        root.title(view.caption)
        root.configure(bg=_BG)
        root.resizable(False, False)

        pad = 24
        wrap = _THUMB_W
        frame = tk.Frame(root, bg=_BG, padx=pad, pady=pad)
        frame.pack(fill="both", expand=True)

        photo = _card_photo(view.image)
        if photo is not None:
            root._photo = photo  # keep a reference
            thumb = tk.Label(frame, image=photo, bg=_BG, bd=0, highlightthickness=0)
            thumb.pack(anchor="w")
            tk.Frame(frame, bg=_RULE, height=1).pack(fill="x", pady=(16, 14))

        tk.Label(
            frame,
            text=view.kicker.upper(),
            bg=_BG,
            fg=_MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            frame,
            text=view.title,
            bg=_BG,
            fg=_INK,
            font=("Georgia", 16),
            wraplength=wrap,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(4, 10))
        tk.Label(
            frame,
            text=view.description,
            bg=_BG,
            fg=_INK,
            font=("Segoe UI", 10),
            wraplength=wrap,
            justify="left",
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            frame,
            text=view.detail,
            bg=_BG,
            fg=_MUTED,
            font=("Segoe UI", 9),
            wraplength=wrap,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(12, 18))

        close = tk.Button(
            frame,
            text="Close",
            command=root.destroy,
            bg=_BTN_BG,
            fg=_BTN_FG,
            activebackground="#3d342c",
            activeforeground=_BTN_FG,
            relief="flat",
            bd=0,
            padx=18,
            pady=7,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        close.pack(anchor="e")
        close.focus_set()

        root.bind("<Escape>", lambda _e: root.destroy())
        root.bind("<Return>", lambda _e: root.destroy())
        _center_window(root)
        root.attributes("-topmost", True)
        root.after(400, lambda: root.attributes("-topmost", False))
        root.mainloop()
        return True
    except Exception as e:
        log.warning("About card failed: %s", e)
        return False


def _card_photo(image: Path | None):
    if image is None:
        return None
    try:
        from PIL import Image, ImageTk

        im = Image.open(image)
        im.thumbnail((_THUMB_W, _THUMB_H), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(im)
    except Exception as e:
        log.warning("About card thumbnail failed: %s", e)
        return None


def _center_window(root) -> None:
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = max(0, (root.winfo_screenwidth() - w) // 2)
    y = max(0, (root.winfo_screenheight() - h) // 2)
    root.geometry(f"+{x}+{y}")


def _enable_dpi_awareness() -> None:
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _show_message_box(caption: str, body: str) -> bool:
    """Windows MessageBox fallback if tkinter cannot run."""
    try:
        import ctypes

        MB_OK = 0x00000000
        MB_ICONINFORMATION = 0x00000040
        MB_SETFOREGROUND = 0x00010000
        MB_TOPMOST = 0x00040000
        ctypes.windll.user32.MessageBoxW(
            None,
            body,
            (caption or "Wallpaper")[:120],
            MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND | MB_TOPMOST,
        )
        return True
    except Exception as e:
        log.warning("About dialog failed: %s", e)
        return False


def show_about_toast(record: JournalRecord | None, image: Path | None) -> bool:
    """Short toast (title + description). Dialog is the full read surface."""
    from rotator.notify import show_toast

    title = (record.title if record else "") or (image.name if image else "Wallpaper")
    message = (record.description if record else "") or "No journal entry for this file."
    if len(message) > 280:
        message = message[:277] + "..."
    return show_toast(title, message, image_path=image)
