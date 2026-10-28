"""Set the Windows desktop wallpaper via ctypes / SystemParametersInfoW."""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from ctypes import wintypes
from pathlib import Path

log = logging.getLogger(__name__)

SPI_SETDESKWALLPAPER = 0x0014
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDWININICHANGE = 0x02
_FLAGS = SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE

_WALLPAPERS_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Wallpapers"


def set_wallpaper(image_path: Path) -> None:
    """Set desktop wallpaper to *image_path*.

    Raises
    ------
    FileNotFoundError
        If the image does not exist.
    OSError
        If SystemParametersInfoW fails or we are not on Windows.
    """
    if sys.platform != "win32":
        raise OSError(f"Wallpaper setting is only supported on Windows (got {sys.platform})")

    path = Path(image_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Wallpaper image not found: {path}")

    # SystemParametersInfoW expects a wide (UTF-16) null-terminated path string
    path_str = str(path)

    # Ensure the DLL call uses Unicode
    result = ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        path_str,
        _FLAGS,
    )

    if not result:
        err = ctypes.get_last_error()
        raise OSError(f"SystemParametersInfoW failed (GetLastError={err}) for {path_str}")

    # Explorer's CurrentWallpaperPath can keep a stale Bing Wallpaper file
    # after that app is uninstalled; a missing path paints a black desktop.
    _sync_current_wallpaper_path(path_str)

    # Explorer's reaction to the wallpaper change can leave TextInputHost's
    # "Windows Input Experience" CoreWindow covering the monitor. That window
    # paints nothing and eats clicks, so icons and the desktop menu vanish.
    hidden = dismiss_blocking_input_overlay(attempts=4, pause_s=0.35)
    if hidden:
        log.info(
            "Hid %s fullscreen Windows Input Experience window(s) covering the desktop",
            hidden,
        )

    log.info("Wallpaper set via SystemParametersInfoW: %s", path_str)


def _sync_current_wallpaper_path(path_str: str) -> None:
    """Keep Explorer's CurrentWallpaperPath in lockstep so a missing Bing file cannot win."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _WALLPAPERS_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, "CurrentWallpaperPath", 0, winreg.REG_SZ, path_str)
            winreg.SetValueEx(key, "BackgroundType", 0, winreg.REG_DWORD, 0)
    except OSError as e:
        log.warning("Could not update CurrentWallpaperPath: %s", e)


# TextInputHost sometimes leaves this CoreWindow the size of the monitor.
# It is not a wallpaper file, and hiding it does not stop the input process
# when ShowWindow succeeds.
_OVERLAY_CLASS = "Windows.UI.Core.CoreWindow"
_OVERLAY_TITLE_MARK = "Input Experience"
_OVERLAY_PROCESS = "textinputhost.exe"
_COVER_FRACTION = 0.80
_SW_HIDE = 0
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_PROCESS_TERMINATE = 0x0001


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


def is_blocking_input_overlay(
    *,
    class_name: str,
    title: str,
    process_name: str,
    visible: bool,
    window: tuple[int, int, int, int],
    monitors: list[tuple[int, int, int, int]],
    min_fraction: float = _COVER_FRACTION,
) -> bool:
    """True when a window is the fullscreen Input Experience overlay.

    A normal touch-keyboard window is the same process and class but only
    covers a strip of the monitor, so size is part of the check.
    """
    if not visible or class_name != _OVERLAY_CLASS:
        return False
    title_hit = _OVERLAY_TITLE_MARK in title
    process_hit = process_name.lower() == _OVERLAY_PROCESS
    if not title_hit and not process_hit:
        return False
    return _covers_monitor(window, monitors, min_fraction)


def _covers_monitor(
    window: tuple[int, int, int, int],
    monitors: list[tuple[int, int, int, int]],
    min_fraction: float,
) -> bool:
    left, top, right, bottom = window
    if right <= left or bottom <= top:
        return False
    for mon_left, mon_top, mon_right, mon_bottom in monitors:
        mon_w = mon_right - mon_left
        mon_h = mon_bottom - mon_top
        if mon_w <= 0 or mon_h <= 0:
            continue
        overlap_w = min(right, mon_right) - max(left, mon_left)
        overlap_h = min(bottom, mon_bottom) - max(top, mon_top)
        if overlap_w <= 0 or overlap_h <= 0:
            continue
        if (overlap_w * overlap_h) >= min_fraction * mon_w * mon_h:
            return True
    return False


def dismiss_blocking_input_overlay(*, attempts: int = 1, pause_s: float = 0.0) -> int:
    """Hide fullscreen Windows Input Experience windows. Returns how many.

    ShowWindow is enough when it sticks. If the window stays visible, the
    TextInputHost process is stopped once; Windows starts it again without
    the fullscreen window.
    """
    if sys.platform != "win32" or attempts < 1:
        return 0

    hidden = 0
    stopped: set[int] = set()
    for index in range(attempts):
        hidden += _dismiss_overlay_once(stopped)
        if pause_s > 0 and index + 1 < attempts:
            time.sleep(pause_s)
    return hidden


_user32 = None
_kernel32 = None


def _win32():
    """user32/kernel32 with scalar prototypes.

    EnumWindows and EnumDisplayMonitors keep their default prototype so each
    call can pass its own callback type.
    """
    global _user32, _kernel32
    if _user32 is not None and _kernel32 is not None:
        return _user32, _kernel32

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(_Rect)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.TerminateProcess.restype = wintypes.BOOL

    _user32 = user32
    _kernel32 = kernel32
    return user32, kernel32


def _dismiss_overlay_once(stopped: set[int]) -> int:
    user32, kernel32 = _win32()
    monitors = _monitor_rects(user32)
    if not monitors:
        return 0

    victims: list[tuple[int, int]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        class_name = _window_class(user32, hwnd)
        title = _window_title(user32, hwnd)
        pid = _window_pid(user32, hwnd)
        process_name = _process_basename(kernel32, pid)
        if is_blocking_input_overlay(
            class_name=class_name,
            title=title,
            process_name=process_name,
            visible=True,
            window=_window_rect(user32, hwnd),
            monitors=monitors,
        ):
            victims.append((int(hwnd), pid))
        return True

    user32.EnumWindows(_enum, 0)

    hidden = 0
    for hwnd, pid in victims:
        if _suppress_overlay_window(user32, kernel32, hwnd, pid, stopped):
            hidden += 1
            log.info(
                "Dismissed fullscreen Windows Input Experience window hwnd=%s pid=%s",
                hwnd,
                pid,
            )
    return hidden


def _suppress_overlay_window(user32, kernel32, hwnd: int, pid: int, stopped: set[int]) -> bool:
    user32.ShowWindow(hwnd, _SW_HIDE)
    if not user32.IsWindowVisible(hwnd):
        return True
    if pid <= 0 or pid in stopped:
        return False
    if _process_basename(kernel32, pid).lower() != _OVERLAY_PROCESS:
        log.warning(
            "Fullscreen Input Experience window hwnd=%s stayed visible and is not TextInputHost",
            hwnd,
        )
        return False
    stopped.add(pid)
    if _terminate_process(kernel32, pid):
        log.warning("Stopped TextInputHost pid=%s after the overlay stayed visible", pid)
        return True
    return False


def _monitor_rects(user32) -> list[tuple[int, int, int, int]]:
    found: list[tuple[int, int, int, int]] = []

    @ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(_Rect),
        wintypes.LPARAM,
    )
    def _enum(hmonitor, _hdc, rect_ptr, _lparam):
        rect = rect_ptr.contents
        found.append((rect.left, rect.top, rect.right, rect.bottom))
        return True

    if not user32.EnumDisplayMonitors(None, None, _enum, 0):
        width = user32.GetSystemMetrics(0)
        height = user32.GetSystemMetrics(1)
        if width > 0 and height > 0:
            return [(0, 0, int(width), int(height))]
    return found


def _window_title(user32, hwnd: int) -> str:
    length = int(user32.GetWindowTextLengthW(hwnd))
    if length < 0:
        length = 0
    if length > 2048:
        length = 2048
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, len(buf))
    return buf.value


def _window_class(user32, hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, len(buf))
    return buf.value


def _window_rect(user32, hwnd: int) -> tuple[int, int, int, int]:
    rect = _Rect()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def _window_pid(user32, hwnd: int) -> int:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def _process_basename(kernel32, pid: int) -> str:
    if pid <= 0:
        return ""
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return ""
        return Path(buf.value).name
    finally:
        kernel32.CloseHandle(handle)


def _terminate_process(kernel32, pid: int) -> bool:
    handle = kernel32.OpenProcess(_PROCESS_TERMINATE, False, pid)
    if not handle:
        return False
    try:
        return bool(kernel32.TerminateProcess(handle, 1))
    finally:
        kernel32.CloseHandle(handle)
