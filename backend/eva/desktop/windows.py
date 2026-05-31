from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from ..tools.desktop import BLOCKED_CLOSE_APP_NAMES, CLOSE_APP_PROCESS_NAMES, close_app_allowlist


SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_RESTORE = 9
WM_CLOSE = 0x0010
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    process_id: int
    process_name: str
    executable: str
    visible: bool = True

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data.pop("hwnd", None)
        return data


def _unsupported() -> bool:
    return os.name != "nt"


if not _unsupported():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM), wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL


def _window_title(hwnd: int) -> str:
    if _unsupported():
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value.strip()


def _process_path(pid: int) -> str:
    if _unsupported() or pid <= 0:
        return ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _process_name(pid: int) -> tuple[str, str]:
    path = _process_path(pid)
    if not path:
        return "", ""
    return Path(path).name, path


def _window_info(hwnd: int) -> WindowInfo | None:
    if _unsupported():
        return None
    title = _window_title(hwnd)
    if not title:
        return None
    visible = bool(user32.IsWindowVisible(hwnd))
    if not visible:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    process_name, executable = _process_name(int(pid.value))
    return WindowInfo(
        hwnd=int(hwnd),
        title=title,
        process_id=int(pid.value),
        process_name=process_name,
        executable=executable,
        visible=visible,
    )


def list_open_windows(limit: int = 80) -> list[WindowInfo]:
    if _unsupported():
        return []
    windows: list[WindowInfo] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd: int, _lparam: int) -> bool:
        if len(windows) >= limit:
            return False
        info = _window_info(hwnd)
        if info is not None:
            windows.append(info)
        return True

    user32.EnumWindows(callback, 0)
    return windows


def get_active_window() -> WindowInfo | None:
    if _unsupported():
        return None
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    return _window_info(int(hwnd))


def _matches(info: WindowInfo, query: str) -> bool:
    clean = " ".join(query.lower().strip().split())
    if not clean:
        return False
    haystack = f"{info.title} {info.process_name} {info.executable}".lower()
    if clean in haystack:
        return True
    for part in clean.split():
        if len(part) >= 3 and part in haystack:
            return True
    return False


def find_window(query: str, limit: int = 10) -> list[WindowInfo]:
    return [window for window in list_open_windows() if _matches(window, query)][:limit]


def _show_window(query: str, command: int) -> dict[str, object]:
    matches = find_window(query, limit=1)
    if not matches:
        return {"ok": False, "error": "window_not_found", "query": query}
    window = matches[0]
    if _unsupported():
        return {"ok": False, "error": "unsupported_platform", "query": query}
    ok = bool(user32.ShowWindow(window.hwnd, command))
    return {"ok": True, "changed": ok, "window": window.as_dict()}


def focus_window(query: str) -> dict[str, object]:
    matches = find_window(query, limit=1)
    if not matches:
        return {"ok": False, "error": "window_not_found", "query": query}
    window = matches[0]
    if _unsupported():
        return {"ok": False, "error": "unsupported_platform", "query": query}
    user32.ShowWindow(window.hwnd, SW_RESTORE)
    focused = bool(user32.SetForegroundWindow(window.hwnd))
    active = get_active_window()
    verified = bool(active and active.hwnd == window.hwnd)
    return {"ok": True, "focused": focused, "verified": verified, "window": window.as_dict(), "active_window": active.as_dict() if active else None}


def minimize_window(query: str) -> dict[str, object]:
    return _show_window(query, SW_SHOWMINIMIZED)


def maximize_window(query: str) -> dict[str, object]:
    return _show_window(query, SW_SHOWMAXIMIZED)


def restore_window(query: str) -> dict[str, object]:
    return _show_window(query, SW_RESTORE)


def _allowed_process_names() -> set[str]:
    allowed: set[str] = set()
    for app in close_app_allowlist():
        for process in CLOSE_APP_PROCESS_NAMES.get(app, ()):
            allowed.add(process.lower())
    return allowed


def _window_close_allowed(window: WindowInfo, query: str) -> tuple[bool, str]:
    process = (window.process_name or "").lower()
    query_clean = " ".join(query.lower().split())
    if query_clean in BLOCKED_CLOSE_APP_NAMES or process in BLOCKED_CLOSE_APP_NAMES:
        return False, "blocked_system_process"
    if process not in _allowed_process_names():
        return False, "not_in_safe_close_allowlist"
    return True, "allowed"


def close_window(query: str) -> dict[str, object]:
    matches = find_window(query, limit=1)
    if not matches:
        return {"ok": False, "error": "window_not_found", "query": query}
    window = matches[0]
    allowed, reason = _window_close_allowed(window, query)
    if not allowed:
        return {"ok": False, "error": reason, "query": query, "window": window.as_dict()}
    posted = bool(user32.PostMessageW(window.hwnd, WM_CLOSE, 0, 0)) if not _unsupported() else False
    return {"ok": posted, "closed": posted, "window": window.as_dict(), "note": "Sent WM_CLOSE to an allowlisted window."}


def windows_as_dicts(windows: Iterable[WindowInfo]) -> list[dict[str, object]]:
    return [window.as_dict() for window in windows]
