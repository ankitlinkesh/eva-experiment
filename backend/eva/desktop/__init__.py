from .observer import DesktopObservation, get_desktop_snapshot
from .skills import (
    close_window_safe,
    desktop_observe,
    focus_window_safe,
    list_windows,
    maximize_window_safe,
    minimize_window_safe,
    active_window,
    verify_last_action,
)
from .verifier import verify_app_opened, verify_folder_opened, verify_url_opened, verify_window_focused
from .windows import WindowInfo, find_window, get_active_window, list_open_windows

__all__ = [
    "DesktopObservation",
    "WindowInfo",
    "active_window",
    "close_window_safe",
    "desktop_observe",
    "find_window",
    "focus_window_safe",
    "get_active_window",
    "get_desktop_snapshot",
    "list_open_windows",
    "list_windows",
    "maximize_window_safe",
    "minimize_window_safe",
    "verify_app_opened",
    "verify_folder_opened",
    "verify_last_action",
    "verify_url_opened",
    "verify_window_focused",
]
