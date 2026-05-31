from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def emit(case: str, passed: bool, **payload: object) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=True))
    return 0 if passed else 1


def main() -> int:
    import backend.eva.api.routes as routes
    from backend.eva.core.intent_router import classify_capability_intent
    from backend.eva.media import spotify
    from backend.eva.tools.registry import ToolRegistry

    failures = 0

    play = classify_capability_intent("play Starboy by The Weeknd on Spotify", {})
    failures += emit(
        "play_spotify_routes_desktop_tool",
        play.get("matched") is True
        and play.get("capability") == "media_music_control"
        and play.get("suggested_route") == "spotify_play_desktop"
        and play.get("query") == "Starboy by The Weeknd",
        result=play,
    )

    search = classify_capability_intent("search Spotify for Blinding Lights", {})
    failures += emit(
        "search_spotify_routes_tool",
        search.get("matched") is True
        and search.get("capability") == "media_music_control"
        and search.get("suggested_route") == "spotify_search_desktop"
        and search.get("query") == "Blinding Lights",
        result=search,
    )

    pause = classify_capability_intent("pause Spotify", {})
    failures += emit(
        "pause_spotify_routes_tool",
        pause.get("matched") is True
        and pause.get("capability") == "media_music_control"
        and pause.get("suggested_route") in {"spotify_pause", "media_control"},
        result=pause,
    )

    registry = ToolRegistry()
    tools = {item["name"]: item for item in registry.list_tools()}
    expected = {
        "spotify_status",
        "spotify_search_desktop",
        "spotify_play_desktop",
        "spotify_pause",
        "spotify_next",
        "spotify_previous",
        "spotify_restart_current",
        "spotify_now_playing_status",
    }
    failures += emit("spotify_tools_registered", expected.issubset(tools), missing=sorted(expected.difference(tools)))
    failures += emit(
        "spotify_tools_have_media_metadata",
        all(
            tools.get(name, {}).get("category") == "media"
            and tools.get(name, {}).get("risk") in {"low", "medium"}
            and tools.get(name, {}).get("verification_strategy")
            and tools.get(name, {}).get("failure_recovery")
            for name in expected
        ),
        specs={name: tools.get(name) for name in sorted(expected)},
    )

    class FakeTools:
        def run(self, name: str, **kwargs: object) -> dict:
            return {"ok": True, "message": f"{name} handled", "kwargs": kwargs}

    old_tools = routes.tools
    try:
        routes.tools = FakeTools()  # type: ignore[assignment]
        route_reply = routes._handle_capability_route("search Spotify for Blinding Lights", search, {}, None, "verify")
    finally:
        routes.tools = old_tools
    failures += emit(
        "capability_handler_returns_spotify_source",
        route_reply is not None and route_reply[1] == "capability:media_music_control",
        reply=route_reply,
    )

    source_files = [
        ROOT / "backend" / "eva" / "media" / "spotify.py",
        ROOT / "backend" / "eva" / "tools" / "registry.py",
        ROOT / "backend" / "eva" / "core" / "intent_router.py",
        ROOT / ".env.example",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in source_files if path.exists())
    failures += emit(
        "no_arbitrary_shell_added",
        "shell=True" not in combined
        and "taskkill" not in combined
        and "Remove-Item" not in combined
        and "Invoke-Expression" not in combined
        and "Start-Process" not in combined,
    )
    failures += emit(
        "desktop_only_no_api_oauth_browser",
        "SPOTIFY_CLIENT_ID" not in combined
        and "SPOTIFY_CLIENT_SECRET" not in combined
        and "SPOTIFY_OAUTH" not in combined
        and "api.spotify.com" not in combined
        and "open.spotify.com" not in (ROOT / "backend" / "eva" / "media" / "spotify.py").read_text(encoding="utf-8"),
    )
    failures += emit(
        "no_random_coordinate_clicks",
        ".click(" not in combined
        and "SetCursorPos" not in combined
        and "mouse_event" not in combined
        and "pyautogui" not in combined,
    )

    original_open = spotify._open_spotify_app
    original_focus = spotify._focus_spotify
    try:
        spotify._open_spotify_app = lambda: (_ for _ in ()).throw(ValueError("Could not find spotify on this laptop."))
        spotify._focus_spotify = lambda: {"ok": False, "error": "window_not_found"}
        unavailable = spotify.open_spotify()
    finally:
        spotify._open_spotify_app = original_open
        spotify._focus_spotify = original_focus
    failures += emit(
        "spotify_unavailable_graceful",
        unavailable.get("ok") is False
        and unavailable.get("error") == "spotify_unavailable"
        and "could not open Spotify" in str(unavailable.get("message")),
        result=unavailable,
    )

    calls: list[tuple[str, object]] = []
    original_open = spotify._open_spotify_app
    original_focus = spotify._focus_spotify
    original_uri = spotify._open_spotify_uri
    original_activate = spotify._activate_selected_spotify_result
    original_now_playing = spotify.spotify_now_playing_status
    original_media_key = spotify.media_key
    try:
        spotify._open_spotify_app = lambda: "Opening spotify."
        spotify._focus_spotify = lambda: {"ok": True, "verified": True}
        spotify._open_spotify_uri = lambda uri: calls.append(("uri", uri)) or {"ok": True, "uri": uri}
        spotify._activate_selected_spotify_result = lambda query: calls.append(("activate", query)) or {"ok": True, "query": query}
        spotify.spotify_now_playing_status = lambda expected_query=None: calls.append(("verify", expected_query)) or {"ok": True, "available": False, "verified": False}
        spotify.media_key = lambda action: calls.append(("media", action)) or f"media:{action}"
        played = spotify.play_spotify_desktop("Starboy by The Weeknd")
    finally:
        spotify._open_spotify_app = original_open
        spotify._focus_spotify = original_focus
        spotify._open_spotify_uri = original_uri
        spotify._activate_selected_spotify_result = original_activate
        spotify.spotify_now_playing_status = original_now_playing
        spotify.media_key = original_media_key
    failures += emit(
        "spotify_play_desktop_activates_result_before_media_key",
        played.get("ok") is True
        and ("uri", "spotify:search:Starboy%20by%20The%20Weeknd") in calls
        and ("activate", "Starboy by The Weeknd") in calls
        and not any(call[0] == "media" for call in calls[: calls.index(("activate", "Starboy by The Weeknd"))])
        and "couldn't verify the exact track" in str(played.get("message")).lower(),
        calls=calls,
        result=played,
    )

    media_calls: list[str] = []
    original_open = spotify._open_spotify_app
    original_focus = spotify._focus_spotify
    original_media_key = spotify.media_key
    try:
        spotify._open_spotify_app = lambda: "Opening spotify."
        spotify._focus_spotify = lambda: {"ok": True, "verified": True}
        spotify.media_key = lambda action: media_calls.append(action) or f"media:{action}"
        restart = spotify.restart_current_spotify_track()
        previous = spotify.previous_spotify_track()
        next_result = spotify.next_spotify()
    finally:
        spotify._open_spotify_app = original_open
        spotify._focus_spotify = original_focus
        spotify.media_key = original_media_key
    failures += emit(
        "restart_previous_next_key_counts",
        restart.get("presses") == 1
        and previous.get("presses") == 2
        and next_result.get("presses") == 1
        and media_calls == ["previous", "previous", "previous", "next"],
        media_calls=media_calls,
        restart=restart,
        previous=previous,
        next=next_result,
    )

    restart_class = classify_capability_intent("restart current song", {})
    start_over_class = classify_capability_intent("start over", {})
    previous_class = classify_capability_intent("previous song", {})
    next_class = classify_capability_intent("next song", {})
    failures += emit(
        "restart_and_previous_routes_split",
        restart_class.get("suggested_route") == "spotify_restart_current"
        and start_over_class.get("suggested_route") == "spotify_restart_current"
        and previous_class.get("suggested_route") == "spotify_previous"
        and next_class.get("suggested_route") == "spotify_next",
        restart=restart_class,
        start_over=start_over_class,
        previous=previous_class,
        next=next_class,
    )

    media_spec = registry.get("media_control")
    failures += emit("existing_media_control_still_registered", media_spec is not None and media_spec.safe_by_default is True)

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
