from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def emit(case: str, passed: bool, **payload: Any) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=False))
    return 0 if passed else 1


def main() -> int:
    import backend.eva.api.routes as routes
    from backend.eva.agent import task_context
    from backend.eva.agent.target_verifier import verify_target
    from backend.eva.apps.playbooks import get_playbook
    from backend.eva.browser import skills as browser_skills
    from backend.eva.core.provenance import provenance_from_source
    from backend.eva.core.intent_router import classify_capability_intent
    from backend.eva.media import spotify
    from backend.eva.screen import screen_tools
    from backend.eva.screen.ui_locator import UiTarget, choose_target
    from backend.eva.tools.registry import ToolRegistry

    failures = 0
    session: dict[str, Any] = {}

    first = classify_capability_intent("play pavazhamalli from youtube", session)
    ctx = task_context.get_current_task_context(session)
    failures += emit(
        "task_context_records_youtube_target",
        first.get("suggested_route") == "chrome_search_site"
        and ctx is not None
        and ctx.target_platform == "youtube"
        and ctx.target_query == "pavazhamalli"
        and ctx.needs_activation is True,
        classification=first,
        context=ctx.as_dict() if ctx else None,
    )

    follow = classify_capability_intent("play it now", session)
    failures += emit(
        "play_it_now_resolves_youtube_not_spotify",
        follow.get("capability") == "browser_agent"
        and follow.get("suggested_route") == "chrome_search_site"
        and follow.get("site") == "youtube"
        and follow.get("query") == "pavazhamalli"
        and follow.get("play") is True,
        result=follow,
    )

    github = classify_capability_intent("search GitHub for AI agents", session)
    verify = classify_capability_intent("can you verify the results", session)
    failures += emit(
        "verify_results_uses_last_browser_target",
        github.get("site") == "github"
        and verify.get("capability") == "browser_agent"
        and verify.get("suggested_route") == "verify_browser_target"
        and verify.get("target_domain") == "github.com",
        github=github,
        verify=verify,
    )

    wrong_tab = verify_target(
        task_context.get_current_task_context(session),
        {"ok": True, "url": "http://127.0.0.1:8765", "title": "Eva - local", "source": "live_probe", "verified": True},
    )
    failures += emit(
        "target_verifier_rejects_wrong_active_tab",
        wrong_tab.verified is False
        and wrong_tab.confidence < 0.7
        and "active Chrome tab is Eva" in (wrong_tab.failure_reason or wrong_tab.evidence),
        result=wrong_tab.as_dict(),
    )

    calls: list[tuple[str, Any]] = []
    original_open = browser_skills.open_url_in_chrome
    original_activate = browser_skills.activate_top_youtube_result
    try:
        browser_skills.open_url_in_chrome = lambda url: calls.append(("open", url)) or {"ok": True, "url": url, "verified": True}
        browser_skills.activate_top_youtube_result = lambda query, task_id=None: calls.append(("activate_youtube", query)) or {
            "ok": True,
            "activated": True,
            "verified": True,
            "url": "https://www.youtube.com/watch?v=test",
            "message": f"Done, I opened the top YouTube result for {query}.",
        }
        youtube_result = browser_skills.chrome_search_site("youtube", "pavazhamalli", play=True)
    finally:
        browser_skills.open_url_in_chrome = original_open
        browser_skills.activate_top_youtube_result = original_activate
    failures += emit(
        "youtube_play_attempts_activation_not_search_only",
        youtube_result.get("ok") is True
        and ("activate_youtube", "pavazhamalli") in calls
        and youtube_result.get("activation", {}).get("verified") is True
        and "top YouTube result" in str(youtube_result.get("message")),
        calls=calls,
        result=youtube_result,
    )

    spotify_calls: list[tuple[str, Any]] = []
    original_open_spotify = spotify._open_spotify_app
    original_focus_spotify = spotify._focus_spotify
    original_uri = spotify._open_spotify_uri
    original_activate_spotify = spotify._activate_selected_spotify_result
    original_now_playing = spotify.spotify_now_playing_status
    original_media = spotify.media_key
    try:
        spotify._open_spotify_app = lambda: "Opening spotify."
        spotify._focus_spotify = lambda: {"ok": True, "verified": True}
        spotify._open_spotify_uri = lambda uri: spotify_calls.append(("uri", uri)) or {"ok": True, "uri": uri}
        spotify._activate_selected_spotify_result = lambda query: spotify_calls.append(("activate", query)) or {
            "ok": True,
            "method": "bounded_visible_keyboard_activation",
            "query": query,
        }
        spotify.spotify_now_playing_status = lambda expected_query=None: spotify_calls.append(("verify", expected_query)) or {
            "ok": True,
            "available": False,
            "verified": False,
            "message": "Now-playing metadata unavailable.",
        }
        spotify.media_key = lambda action: spotify_calls.append(("media", action)) or f"media:{action}"
        played = spotify.play_spotify_desktop("pavazhamalli")
    finally:
        spotify._open_spotify_app = original_open_spotify
        spotify._focus_spotify = original_focus_spotify
        spotify._open_spotify_uri = original_uri
        spotify._activate_selected_spotify_result = original_activate_spotify
        spotify.spotify_now_playing_status = original_now_playing
        spotify.media_key = original_media
    failures += emit(
        "spotify_play_activates_result_before_media_key",
        played.get("ok") is True
        and ("activate", "pavazhamalli") in spotify_calls
        and not any(call[0] == "media" for call in spotify_calls[: spotify_calls.index(("activate", "pavazhamalli"))])
        and "searched Spotify" in str(played.get("message")),
        calls=spotify_calls,
        result=played,
    )

    media_calls: list[str] = []
    original_open_spotify = spotify._open_spotify_app
    original_focus_spotify = spotify._focus_spotify
    original_media = spotify.media_key
    try:
        spotify._open_spotify_app = lambda: "Opening spotify."
        spotify._focus_spotify = lambda: {"ok": True, "verified": True}
        spotify.media_key = lambda action: media_calls.append(action) or f"media:{action}"
        restart = spotify.restart_current_spotify_track()
        previous = spotify.previous_spotify_track()
    finally:
        spotify._open_spotify_app = original_open_spotify
        spotify._focus_spotify = original_focus_spotify
        spotify.media_key = original_media
    failures += emit(
        "spotify_restart_previous_counts_stay_split",
        restart.get("presses") == 1 and previous.get("presses") == 2 and media_calls == ["previous", "previous", "previous"],
        calls=media_calls,
    )

    no_reason = screen_tools.screen_observe("")
    low_target = UiTarget(
        target_id="low",
        label="Play",
        role="button",
        x=10,
        y=10,
        width=20,
        height=20,
        confidence=0.4,
        method="heuristic",
        app="Chrome",
        window_title="YouTube",
    )
    low_click = screen_tools.screen_click(target=low_target.as_dict(), reason="verify low confidence")
    raw_click = screen_tools.screen_click(x=10, y=10, reason="raw coordinate attempt")
    chosen = choose_target({"ui_targets": [low_target.as_dict()]}, "play", required_confidence=0.75)
    failures += emit(
        "visual_control_requires_reason_and_confident_target",
        no_reason.get("ok") is False
        and low_click.get("ok") is False
        and raw_click.get("ok") is False
        and chosen is None,
        no_reason=no_reason,
        low_click=low_click,
        raw_click=raw_click,
    )

    chatgpt = classify_capability_intent("ask ChatGPT on my Chrome for money making ideas", session)
    chatgpt_reply = routes._handle_capability_route("ask ChatGPT on my Chrome for money making ideas", chatgpt, session, None, "verify")
    failures += emit(
        "chatgpt_in_chrome_does_not_answer_directly",
        chatgpt.get("suggested_route") == "chatgpt_in_chrome"
        and chatgpt_reply is not None
        and chatgpt_reply[1] in {"capability:chatgpt_in_chrome", "capability:chatgpt_in_chrome_unavailable"}
        and "can't yet reliably" in chatgpt_reply[0],
        classification=chatgpt,
        reply=chatgpt_reply,
    )
    failures += emit(
        "chatgpt_unavailable_not_marked_as_chatgpt_provenance",
        provenance_from_source("capability:chatgpt_in_chrome_unavailable", ["chatgpt_in_chrome"]) != "chatgpt_in_chrome",
    )

    private_chatgpt = browser_skills.ask_chatgpt_in_chrome("summarize my local file C:\\Users\\HP\\Documents\\secret.txt")
    failures += emit(
        "private_chatgpt_prompt_requires_confirmation",
        private_chatgpt.get("ok") is False
        and private_chatgpt.get("requires_confirmation") is True
        and private_chatgpt.get("provenance") != "chatgpt_in_chrome",
        result=private_chatgpt,
    )

    whatsapp = classify_capability_intent("send a WhatsApp message saying hello to raks", session)
    whatsapp_reply = routes._handle_capability_route("send a WhatsApp message saying hello to raks", whatsapp, session, None, "verify")
    failures += emit(
        "whatsapp_prefers_desktop_and_requires_confirmation",
        whatsapp.get("capability") == "message_workflow"
        and whatsapp_reply is not None
        and "WhatsApp Desktop is the first target" in whatsapp_reply[0]
        and "requires confirmation" in whatsapp_reply[0]
        and "will not send it silently" in whatsapp_reply[0],
        classification=whatsapp,
        reply=whatsapp_reply,
    )

    for name in ("chrome", "youtube", "chatgpt", "spotify", "whatsapp", "notepad", "vscode", "file explorer"):
        failures += emit(
            f"playbook_{name.replace(' ', '_')}_exists",
            get_playbook(name) is not None,
            playbook=get_playbook(name).as_dict() if get_playbook(name) else None,
        )

    registry = ToolRegistry()
    specs = {item["name"]: item for item in registry.list_tools()}
    required_tools = {
        "browser_verify_target",
        "chrome_activate_top_youtube_result",
        "spotify_now_playing_status",
        "screen.observe",
        "screen.click",
    }
    failures += emit("visual_tools_registered", required_tools.issubset(specs), missing=sorted(required_tools.difference(specs)))

    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in [
            ROOT / "backend" / "eva" / "browser" / "skills.py",
            ROOT / "backend" / "eva" / "browser" / "controller.py",
            ROOT / "backend" / "eva" / "media" / "spotify.py",
            ROOT / "backend" / "eva" / "screen" / "screen_tools.py",
            ROOT / "backend" / "eva" / "screen" / "screen_controller.py",
            ROOT / "backend" / "eva" / "core" / "intent_router.py",
        ]
        if path.exists()
    )
    banned = ("document.cookie", "localstorage", "sessionstorage", "get-cookie", "authorization:", "bearer ")
    failures += emit(
        "no_cookie_token_localstorage_reads",
        not any(item in source_text for item in banned),
        found=[item for item in banned if item in source_text],
    )
    failures += emit(
        "no_default_arbitrary_shell_path_added",
        "shell=true" not in source_text and "invoke-expression" not in source_text,
    )
    failures += emit(
        "no_always_on_screen_capture",
        "while true" not in source_text and "capture_interval_ms" not in source_text,
    )

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
