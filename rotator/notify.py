"""Native Windows toast notifications via windows-toasts (optional dependency).

Some generation failures also get a MessageBox. The desktop New command's
console closes as soon as the process exits, so a printed error is easy to miss.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Phrases from the xAI 403 body. Match these, not a bare HTTP 403
# (a bad key or a moderation block must not look like a billing dialog).
_CREDIT_PHRASES = (
    "used all available credits",
    "purchase more credits",
    "raise your spending limit",
    "monthly spending limit",
    "insufficient credits",
    "out of credits",
)

_CREDIT_TITLE = "No xAI credits"
_CREDIT_BODY = (
    "xAI refused this wallpaper. The team has no credits left, "
    "or it has reached the monthly spending limit.\n\n"
    "Nothing new was generated. The desktop was left as it was.\n\n"
    "Add credits or raise the limit at console.x.ai, "
    "then click New Grok wallpaper again."
)

# Shown only after literary and painting have each already retried Imagine once.
_MODERATION_TITLE = "Image blocked"
_MODERATION_BODY = (
    "Imagine rejected this wallpaper, and a second scene was rejected too.\n\n"
    "Nothing new was generated. The desktop was left as it was.\n\n"
    "This is not a credits problem. Click New Grok wallpaper again "
    "to try another scene."
)

# Phrases from chat/image URLErrors and from raw download failures
# (the image-bytes downloader does not wrap those as "network error").
_OFFLINE_PHRASES = (
    "network error",
    "getaddrinfo failed",
    "urlopen error",
    "timed out",
    "unexpected_eof",
    "connection refused",
    "connection reset",
    "network is unreachable",
    "name or service not known",
    "temporary failure in name resolution",
    "nodename nor servname",
    "winerror 10060",
    "winerror 10061",
    "errno 11001",
)

_OFFLINE_TITLE = "Couldn't reach xAI"
_OFFLINE_BODY = (
    "This computer could not reach xAI, so no wallpaper was generated.\n\n"
    "Nothing new was saved. The desktop was left as it was.\n\n"
    "Check the network connection, then click New Grok wallpaper again."
)


def show_toast(title: str, message: str, image_path: Path | None = None) -> bool:
    """Show a toast. Returns True on success, False if library missing or toast fails.

    Never raises — notifications must not break the rotator.
    """
    try:
        from windows_toasts import Toast, WindowsToaster
    except ImportError:
        log.debug("windows-toasts not installed; skipping notification")
        return False

    try:
        toaster = WindowsToaster(title)
        toast = Toast()
        toast.text_fields = [title, message]

        if image_path is not None and Path(image_path).is_file():
            try:
                from windows_toasts import ToastDisplayImage

                # fromPath accepts str or PathLike (windows-toasts ≥1.x)
                toast.AddImage(
                    ToastDisplayImage.fromPath(str(Path(image_path).resolve()))
                )
            except Exception as e:
                log.debug("Toast image attach skipped: %s", e)

        toaster.show_toast(toast)
        log.debug("Toast shown: %s — %s", title, message)
        return True
    except Exception as e:
        log.warning("Toast notification failed: %s", e)
        return False


def is_xai_credit_block(message: str) -> bool:
    """True when *message* is xAI refusing for credits or a spending cap."""
    text = (message or "").lower()
    return any(phrase in text for phrase in _CREDIT_PHRASES)


def is_content_moderated(message: str) -> bool:
    """True when the final error is Imagine's content-moderation refusal.

    Literary and painting swallow the first refusal and retry. This matches
    only the error that escapes, which is the second block.
    """
    return "content-moderated" in (message or "").lower()


def is_offline_failure(message: str) -> bool:
    """True when generation died because xAI could not be reached."""
    text = (message or "").lower()
    if is_xai_credit_block(text) or is_content_moderated(text):
        return False
    return any(phrase in text for phrase in _OFFLINE_PHRASES)


def alert_if_credit_block(message: str, *, timeout_ms: int | None = None) -> bool:
    """Show the no-credits dialog. Returns True if it was shown.

    Never raises. ``timeout_ms`` auto-dismisses the box (midnight task, so a
    locked session cannot hold the job until Task Scheduler kills it).
    ``None`` waits until the user clicks OK.
    """
    if not is_xai_credit_block(message):
        return False
    return _show_named("no-credits", _CREDIT_TITLE, _CREDIT_BODY, timeout_ms)


def alert_if_content_moderated(message: str, *, timeout_ms: int | None = None) -> bool:
    """Show the moderation dialog. Returns True if it was shown. Never raises."""
    if not is_content_moderated(message):
        return False
    return _show_named("content-moderation", _MODERATION_TITLE, _MODERATION_BODY, timeout_ms)


def alert_if_offline(message: str, *, timeout_ms: int | None = None) -> bool:
    """Show the offline dialog. Returns True if it was shown. Never raises."""
    if not is_offline_failure(message):
        return False
    return _show_named("offline", _OFFLINE_TITLE, _OFFLINE_BODY, timeout_ms)


def alert_generation_failure(message: str, *, timeout_ms: int | None = None) -> bool:
    """One dialog for a failed New or midnight run.

    Credits win over moderation over offline. Anything else stays in the log.
    """
    if is_xai_credit_block(message):
        return alert_if_credit_block(message, timeout_ms=timeout_ms)
    if is_content_moderated(message):
        return alert_if_content_moderated(message, timeout_ms=timeout_ms)
    if is_offline_failure(message):
        return alert_if_offline(message, timeout_ms=timeout_ms)
    return False


def _show_named(kind: str, title: str, body: str, timeout_ms: int | None) -> bool:
    shown = show_alert(title, body, timeout_ms=timeout_ms)
    if shown:
        log.info("Showed %s dialog", kind)
    else:
        log.warning("%s dialog could not be shown", kind)
    return shown


def show_alert(title: str, body: str, *, timeout_ms: int | None = None) -> bool:
    """Windows MessageBox. Returns False if the box could not be opened."""
    try:
        import ctypes

        MB_OK = 0x00000000
        MB_ICONWARNING = 0x00000030
        MB_SETFOREGROUND = 0x00010000
        MB_TOPMOST = 0x00040000
        flags = MB_OK | MB_ICONWARNING | MB_SETFOREGROUND | MB_TOPMOST
        user32 = ctypes.windll.user32
        if timeout_ms:
            try:
                fn = user32.MessageBoxTimeoutW
                fn.argtypes = [
                    ctypes.c_void_p,
                    ctypes.c_wchar_p,
                    ctypes.c_wchar_p,
                    ctypes.c_uint,
                    ctypes.c_ushort,
                    ctypes.c_uint,
                ]
                fn.restype = ctypes.c_int
                fn(None, body, title[:120], flags, 0, int(timeout_ms))
                return True
            except (AttributeError, OSError) as e:
                log.warning("Timed message box unavailable (%s); not blocking", e)
                return False
        user32.MessageBoxW(None, body, (title or "Wallpaper")[:120], flags)
        return True
    except Exception as e:
        log.warning("Message box failed: %s", e)
        return False
