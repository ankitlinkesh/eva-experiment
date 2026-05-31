from __future__ import annotations

from typing import Any

from ..browser.skills import browser_open_url, browser_search
from ..desktop import focus_window_safe
from .desktop import close_app, open_app


def app_open(app: str) -> dict[str, Any]:
    return {"ok": True, "message": open_app(app)}


def app_focus(query: str) -> dict[str, Any]:
    return focus_window_safe(query)


def app_close_request(app: str, confirmed: bool = False) -> dict[str, Any]:
    if not confirmed:
        return {"ok": False, "requires_confirmation": True, "message": f"Closing {app} may lose unsaved work. Confirm first."}
    return {"ok": True, "message": close_app(app)}


def browser_open_url_tool(url: str) -> dict[str, Any]:
    return browser_open_url(url)


def browser_search_tool(query: str) -> dict[str, Any]:
    return browser_search(query)
