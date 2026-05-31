from __future__ import annotations

from typing import Any

from .observer import get_desktop_snapshot
from .verifier import verify_app_opened, verify_folder_opened, verify_url_opened, verify_window_focused
from .windows import close_window, find_window, focus_window, get_active_window, list_open_windows, maximize_window, minimize_window, windows_as_dicts


def desktop_observe(include_windows: bool = True, include_screen: bool = False, explicit_screen_intent: bool = False) -> dict[str, Any]:
    return get_desktop_snapshot(
        include_windows=bool(include_windows),
        include_screen=bool(include_screen),
        explicit_screen_intent=bool(explicit_screen_intent),
    )


def list_windows(limit: int = 40) -> dict[str, Any]:
    windows = list_open_windows(limit=int(limit or 40))
    return {"ok": True, "count": len(windows), "windows": windows_as_dicts(windows)}


def active_window() -> dict[str, Any]:
    active = get_active_window()
    if active is None:
        return {"ok": False, "error": "active_window_unavailable"}
    return {"ok": True, "window": active.as_dict()}


def focus_window_safe(query: str) -> dict[str, Any]:
    return focus_window(str(query))


def minimize_window_safe(query: str) -> dict[str, Any]:
    return minimize_window(str(query))


def maximize_window_safe(query: str) -> dict[str, Any]:
    return maximize_window(str(query))


def close_window_safe(query: str) -> dict[str, Any]:
    return close_window(str(query))


def verify_last_action(action: str = "", target: str = "", tool: str = "") -> dict[str, Any]:
    clean_tool = (tool or action).strip().lower()
    if clean_tool in {"open_app", "app"}:
        return verify_app_opened(target)
    if clean_tool in {"open_folder", "folder"}:
        return verify_folder_opened(target)
    if clean_tool in {"open_url", "url"}:
        return verify_url_opened(target)
    if clean_tool in {"focus_window", "window_focus", "focus"}:
        return verify_window_focused(target)
    return {"ok": False, "verified": False, "error": "unsupported_verification", "action": action, "tool": tool, "target": target}


def find_window_safe(query: str) -> dict[str, Any]:
    matches = find_window(str(query))
    return {"ok": True, "query": query, "count": len(matches), "matches": windows_as_dicts(matches)}
