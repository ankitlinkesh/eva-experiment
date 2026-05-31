from __future__ import annotations

import os
import subprocess
import time
import urllib.parse
from typing import Any

from ..agent.task_context import update_task_context
from ..desktop import focus_window_safe, list_open_windows
from ..tools.desktop import media_key, open_app


SPOTIFY_QUERY_LIMIT = 160
SPOTIFY_SEARCH_LOAD_SECONDS = 0.9
SPOTIFY_PLAY_STEP_SECONDS = 0.35
SPOTIFY_PREVIOUS_DELAY_SECONDS = 0.45


def _open_spotify_app() -> str:
    return open_app("spotify")


def _focus_spotify() -> dict[str, Any]:
    return focus_window_safe("spotify")


def _spotify_windows() -> list[dict[str, Any]]:
    windows = []
    for window in list_open_windows(limit=80):
        item = window.as_dict() if hasattr(window, "as_dict") else dict(window)
        haystack = f"{item.get('title', '')} {item.get('process_name', '')} {item.get('executable', '')}".lower()
        if "spotify" in haystack:
            windows.append(item)
    return windows


def _clean_query(query: str) -> str:
    clean = " ".join(str(query or "").strip().split())
    if not clean:
        raise ValueError("Spotify query is empty.")
    return clean[:SPOTIFY_QUERY_LIMIT]


def _open_spotify_uri(uri: str) -> dict[str, Any]:
    if not uri.startswith("spotify:"):
        return {"ok": False, "error": "unsafe_spotify_uri"}
    if os.name != "nt":
        return {"ok": False, "error": "unsupported_platform", "message": "Spotify URI automation is only wired for Windows in v1."}
    try:
        os.startfile(uri)  # type: ignore[attr-defined]
    except Exception as exc:
        return {"ok": False, "error": "spotify_uri_open_failed", "detail": str(exc)[:160]}
    return {"ok": True, "uri": uri, "method": "spotify_uri"}


def _send_visible_keys(keys: str, *, delay_ms: int = 120) -> dict[str, Any]:
    """Send a fixed, bounded key sequence to the visible foreground app."""
    allowed = {
        "{ENTER}",
        " ",
    }
    if keys not in allowed:
        return {"ok": False, "error": "unsupported_key_sequence"}
    ps = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Start-Sleep -Milliseconds {int(delay_ms)}
[System.Windows.Forms.SendKeys]::SendWait('{keys}')
"""
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=4,
        )
    except Exception as exc:
        return {"ok": False, "error": "sendkeys_failed", "detail": str(exc)[:160]}
    return {"ok": completed.returncode == 0, "method": "visible_sendkeys", "keys": keys, "returncode": completed.returncode}


def spotify_status() -> dict[str, Any]:
    windows = _spotify_windows()
    focused = _focus_spotify() if windows else {"ok": False, "error": "spotify_window_not_found"}
    return {
        "ok": True,
        "installed_or_openable": True,
        "open": bool(windows),
        "windows": windows[:5],
        "focus": focused,
        "verification_strategy": "Visible Spotify window detection through Desktop Agent Core.",
        "privacy_note": "Does not read Spotify cookies, tokens, account data, or private storage.",
    }


def open_spotify() -> dict[str, Any]:
    try:
        opened = _open_spotify_app()
    except Exception as exc:
        return {
            "ok": False,
            "error": "spotify_unavailable",
            "message": f"I could not open Spotify on this laptop: {str(exc)[:160]}",
            "recovery": "Install Spotify or open it manually, then ask Eva again.",
        }
    time.sleep(0.4)
    focus = _focus_spotify()
    return {
        "ok": True,
        "opened": opened,
        "focus": focus,
        "verified": bool(focus.get("ok") and (focus.get("verified") is not False)),
        "message": "Spotify is open." if focus.get("ok") else "Spotify was opened, but I could not verify/focus its window yet.",
    }


def search_spotify_desktop(query: str) -> dict[str, Any]:
    clean = _clean_query(query)
    update_task_context(
        user_request=f"search Spotify for {clean}",
        active_intent="search",
        target_app="spotify",
        target_platform="spotify",
        target_query=clean,
        expected_result=f"Spotify search results for {clean}",
        needs_activation=False,
        last_tool="spotify_search_desktop",
        provenance="tool_result",
    )
    opened = open_spotify()
    if not opened.get("ok"):
        return opened
    uri = "spotify:search:" + urllib.parse.quote(clean, safe="")
    uri_result = _open_spotify_uri(uri)
    time.sleep(SPOTIFY_SEARCH_LOAD_SECONDS)
    focus = _focus_spotify()
    ok = bool(uri_result.get("ok"))
    return {
        "ok": ok,
        "query": clean,
        "opened": opened,
        "search": uri_result,
        "focus": focus,
        "verified": False,
        "message": (
            f"I searched Spotify for {clean}. I couldn't verify the exact result yet."
            if ok
            else f"Spotify is open, but I couldn't safely search for {clean}."
        ),
        "verification_note": "Spotify desktop v1.1 can open a bounded spotify:search URI, but it cannot read Spotify playback state.",
    }


def search_spotify(query: str) -> dict[str, Any]:
    return search_spotify_desktop(query)


def play_spotify_desktop(query: str) -> dict[str, Any]:
    searched = search_spotify_desktop(query)
    if not searched.get("ok"):
        return searched
    clean = str(searched.get("query") or query)
    update_task_context(
        user_request=f"play {clean} on Spotify",
        active_intent="play",
        target_app="spotify",
        target_platform="spotify",
        target_query=clean,
        expected_result=f"Spotify playing {clean}",
        needs_activation=True,
        last_tool="spotify_play_desktop",
        provenance="tool_result",
    )
    focus = _focus_spotify()
    activation = _activate_selected_spotify_result(clean) if focus.get("ok") else {"ok": False, "error": "spotify_not_focused"}
    time.sleep(SPOTIFY_PLAY_STEP_SECONDS)
    now_playing = spotify_now_playing_status(expected_query=clean)
    verified = bool(now_playing.get("verified"))
    if verified:
        message = str(now_playing.get("message") or f"Done, playing {clean} on Spotify.")
    elif activation.get("ok"):
        message = f"I searched Spotify for {clean} and activated the selected result, but I couldn't verify the exact track yet."
    else:
        message = f"I searched Spotify for {clean}, but I couldn't safely activate the result."
    return {
        "ok": True,
        "query": clean,
        "search": searched,
        "play_attempt": {
            "activation": activation,
            "now_playing": now_playing,
        },
        "verified": verified,
        "message": message,
        "verification_note": "Playback uses Spotify desktop only: spotify:search URI, focus verification, bounded Enter activation, and local now-playing/window checks when available. No browser, API, OAuth, tokens, cookies, random clicks, or immediate global play/pause after search.",
        "ui_events": [
            {"type": "locating_ui_target", "target": "spotify_selected_result"},
            {"type": "executing_visible_action", "action": "activate_selected_spotify_result"},
            {"type": "verifying_target", "target": "spotify_now_playing"},
            {"type": "verification_passed" if verified else "verification_failed", "confidence": 0.8 if verified else 0.35},
        ],
    }


def play_spotify_query(query: str) -> dict[str, Any]:
    return play_spotify_desktop(query)


def pause_spotify() -> dict[str, Any]:
    open_result = open_spotify()
    if not open_result.get("ok"):
        return open_result
    result = media_key("play_pause")
    return {"ok": True, "action": "pause", "presses": 1, "message": "Sent Spotify play/pause media key.", "result": result, "verified": False}


def next_spotify() -> dict[str, Any]:
    open_result = open_spotify()
    if not open_result.get("ok"):
        return open_result
    result = media_key("next")
    return {"ok": True, "action": "next", "presses": 1, "message": "Sent Spotify next media key once.", "result": result, "verified": False}


def restart_current_spotify_track() -> dict[str, Any]:
    open_result = open_spotify()
    if not open_result.get("ok"):
        return open_result
    result = media_key("previous")
    return {"ok": True, "action": "restart_current", "presses": 1, "message": "Sent Spotify previous media key once to restart the current song.", "result": result, "verified": False}


def previous_spotify_track() -> dict[str, Any]:
    open_result = open_spotify()
    if not open_result.get("ok"):
        return open_result
    first = media_key("previous")
    time.sleep(SPOTIFY_PREVIOUS_DELAY_SECONDS)
    second = media_key("previous")
    return {
        "ok": True,
        "action": "previous",
        "presses": 2,
        "message": "Sent Spotify previous media key twice to request the previous track.",
        "result": [first, second],
        "verified": False,
    }


def previous_spotify() -> dict[str, Any]:
    return previous_spotify_track()


def _activate_selected_spotify_result(query: str) -> dict[str, Any]:
    """Activate the currently selected Spotify search result using visible bounded input."""
    first_enter = _send_visible_keys("{ENTER}", delay_ms=120)
    if not first_enter.get("ok"):
        return {"ok": False, "method": "bounded_visible_keyboard_activation", "step": "enter", "result": first_enter}
    time.sleep(SPOTIFY_PLAY_STEP_SECONDS)
    second_enter = _send_visible_keys("{ENTER}", delay_ms=120)
    return {
        "ok": bool(second_enter.get("ok")),
        "method": "bounded_visible_keyboard_activation",
        "query": query,
        "sequence": [first_enter, second_enter],
        "verification_note": "Used Enter on the visible Spotify search result area only; no random coordinate click.",
    }


def spotify_now_playing_status(expected_query: str | None = None) -> dict[str, Any]:
    windows = _spotify_windows()
    clean_expected = " ".join(str(expected_query or "").strip().lower().split())
    title = str(windows[0].get("title") or "") if windows else ""
    title_lower = title.lower()
    if clean_expected and title and all(part in title_lower for part in clean_expected.split()[:3]):
        return {
            "ok": True,
            "available": True,
            "verified": True,
            "source": "spotify_window_title",
            "title": title,
            "message": f"Done, Spotify appears to be playing {expected_query}.",
        }
    return {
        "ok": True,
        "available": False,
        "verified": False,
        "source": "media_session",
        "windows": windows[:3],
        "message": "Spotify now-playing metadata is not available from this desktop adapter yet.",
    }
