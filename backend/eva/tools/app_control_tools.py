from __future__ import annotations

from typing import Any

from ..browser.skills import browser_open_url, browser_search
from ..desktop import focus_window_safe


def app_focus(query: str) -> dict[str, Any]:
    return focus_window_safe(query)


def browser_open_url_tool(url: str) -> dict[str, Any]:
    return browser_open_url(url)


def browser_search_tool(query: str) -> dict[str, Any]:
    return browser_search(query)
