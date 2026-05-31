from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.browser.web_apps import build_site_search_url, resolve_web_app
from backend.eva.browser import skills as browser_skills
from backend.eva.agent.executor import ToolExecutionResult
from backend.eva.api.routes import _local_tool_summary
from backend.eva.core.intent_router import classify_capability_intent
from backend.eva.tools.registry import ToolRegistry


def emit(case: str, passed: bool, **payload: Any) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=False))
    return 0 if passed else 1


def main() -> int:
    failures = 0
    registry = ToolRegistry()
    specs = {item["name"]: item for item in registry.list_tools()}

    chatgpt = classify_capability_intent("open ChatGPT on Chrome", {})
    failures += emit(
        "open_chatgpt_routes_chrome_web_app",
        bool(
            chatgpt.get("matched")
            and chatgpt.get("capability") == "browser_agent"
            and chatgpt.get("suggested_route") in {"chrome_open_web_app", "browser_open_url"}
            and chatgpt.get("app") == "chatgpt"
        ),
        result=chatgpt,
    )

    chrome_summary = _local_tool_summary(
        [
            ToolExecutionResult(
                tool="chrome_open_web_app",
                ok=True,
                result={"ok": True, "app_name": "ChatGPT", "url": "https://chatgpt.com", "verified": True, "message": "Done, ChatGPT is open in Chrome."},
            )
        ]
    )
    failures += emit(
        "chrome_open_web_app_summary_is_clean",
        bool(
            chrome_summary == "Done, ChatGPT is open in Chrome."
            and "{'ok':" not in chrome_summary
            and "verification" not in chrome_summary.lower()
        ),
        summary=chrome_summary,
    )

    unverified_summary = _local_tool_summary(
        [
            ToolExecutionResult(
                tool="chrome_open_web_app",
                ok=True,
                result={"ok": True, "app_name": "ChatGPT", "url": "https://chatgpt.com", "verified": False},
            )
        ]
    )
    failures += emit(
        "chrome_open_web_app_unverified_summary_is_clean",
        bool(
            unverified_summary
            == "Done, ChatGPT is open in Chrome. I couldn't verify the exact browser URL from Windows, but the open action completed."
            and "{'ok':" not in unverified_summary
        ),
        summary=unverified_summary,
    )

    gmail = resolve_web_app("gmail")
    failures += emit(
        "gmail_resolves_mail_google",
        bool(gmail and gmail.get("url") == "https://mail.google.com"),
        result=gmail,
    )

    youtube_url = build_site_search_url("youtube", "Interstellar theme")
    youtube = classify_capability_intent("open YouTube and search Interstellar theme", {})
    failures += emit(
        "youtube_search_builds_results_url",
        bool(
            youtube_url == "https://www.youtube.com/results?search_query=Interstellar+theme"
            and youtube.get("suggested_route") == "chrome_search_site"
            and youtube.get("site") == "youtube"
            and youtube.get("query") == "Interstellar theme"
        ),
        url=youtube_url,
        result=youtube,
    )

    youtube_play_from = classify_capability_intent("play pavazhamalli from youtube", {})
    youtube_play_on = classify_capability_intent("play pavazhamalli on youtube", {})
    failures += emit(
        "youtube_play_from_routes_chrome_not_spotify",
        bool(
            youtube_play_from.get("matched")
            and youtube_play_from.get("capability") == "browser_agent"
            and youtube_play_from.get("suggested_route") == "chrome_search_site"
            and youtube_play_from.get("site") == "youtube"
            and youtube_play_from.get("query") == "pavazhamalli"
            and youtube_play_from.get("play") is True
        ),
        result=youtube_play_from,
    )
    failures += emit(
        "youtube_play_on_routes_chrome_not_spotify",
        bool(
            youtube_play_on.get("matched")
            and youtube_play_on.get("capability") == "browser_agent"
            and youtube_play_on.get("suggested_route") == "chrome_search_site"
            and youtube_play_on.get("site") == "youtube"
            and youtube_play_on.get("query") == "pavazhamalli"
            and youtube_play_on.get("play") is True
        ),
        result=youtube_play_on,
    )

    activation_calls: list[tuple[str, object]] = []
    old_open = browser_skills.open_url_in_chrome
    old_activate = browser_skills.activate_top_youtube_result
    try:
        browser_skills.open_url_in_chrome = lambda url: activation_calls.append(("open", url)) or {"ok": True, "url": url, "verified": True}
        browser_skills.activate_top_youtube_result = lambda query, task_id=None: activation_calls.append(("activate", query)) or {"ok": True, "verified": True, "message": f"Done, I opened the top YouTube result for {query}."}
        activation_result = browser_skills.chrome_search_site("youtube", "pavazhamalli", play=True)
    finally:
        browser_skills.open_url_in_chrome = old_open
        browser_skills.activate_top_youtube_result = old_activate
    failures += emit(
        "youtube_play_workflow_attempts_activation",
        ("activate", "pavazhamalli") in activation_calls
        and "top YouTube result" in str(activation_result.get("message")),
        calls=activation_calls,
        result=activation_result,
    )

    github_url = build_site_search_url("github", "AI agents")
    github = classify_capability_intent("search GitHub for AI agents", {})
    failures += emit(
        "github_search_builds_search_url",
        bool(
            github_url == "https://github.com/search?q=AI+agents"
            and github.get("suggested_route") == "chrome_search_site"
            and github.get("site") == "github"
            and github.get("query") == "AI agents"
        ),
        url=github_url,
        result=github,
    )

    spotify_play = classify_capability_intent("play pavazhamalli on Spotify", {})
    failures += emit(
        "spotify_explicit_play_still_routes_spotify",
        bool(
            spotify_play.get("matched")
            and spotify_play.get("capability") == "media_music_control"
            and spotify_play.get("suggested_route") == "spotify_play_desktop"
            and spotify_play.get("query") == "pavazhamalli"
        ),
        result=spotify_play,
    )

    copy_url = classify_capability_intent("copy current URL", {})
    failures += emit(
        "copy_current_url_routes_current_url_flow",
        bool(copy_url.get("matched") and copy_url.get("suggested_route") == "chrome_copy_current_url"),
        result=copy_url,
    )

    summary = classify_capability_intent("summarize this page", {})
    failures += emit(
        "summarize_this_page_routes_browser_summary",
        bool(summary.get("matched") and summary.get("suggested_route") == "browser_summarize_page"),
        result=summary,
    )

    save = classify_capability_intent("save this page to research topic test", {})
    failures += emit(
        "save_page_routes_research_save",
        bool(
            save.get("matched")
            and save.get("suggested_route") == "browser_save_page_to_research"
            and save.get("topic") == "test"
        ),
        result=save,
    )

    failures += emit(
        "private_non_http_urls_refused",
        _raises(lambda: registry.run("browser_open_result_and_verify", url="file:///C:/Users/HP/.env")),
    )

    chrome_tools = {
        "chrome_open_web_app",
        "chrome_open_web_app_and_verify",
        "chrome_search_site",
        "chrome_search_site_and_verify",
        "chrome_activate_top_youtube_result",
        "chrome_copy_current_url",
        "chrome_new_tab",
        "chrome_close_tab",
        "chrome_reload",
        "chrome_back",
        "chrome_forward",
        "chrome_focus_address_bar",
        "browser_open_result_and_verify",
        "browser_verify_target",
        "browser_recover_target",
        "chatgpt_in_chrome",
    }
    missing = sorted(chrome_tools.difference(specs))
    failures += emit("chrome_tools_registered", not missing, missing=missing)

    combined = "\n".join(
        Path(path).read_text(encoding="utf-8", errors="replace").lower()
        for path in [
            ROOT / "backend" / "eva" / "browser" / "web_apps.py",
            ROOT / "backend" / "eva" / "browser" / "skills.py",
            ROOT / "backend" / "eva" / "browser" / "controller.py",
            ROOT / "backend" / "eva" / "tools" / "registry.py",
            ROOT / "backend" / "eva" / "core" / "intent_router.py",
        ]
        if Path(path).exists()
    )
    banned = (
        "document.cookie",
        "get-cookie",
        "get_cookie",
        "localstorage.",
        "localstorage[",
        "sessionstorage.",
        "password.value",
        "authorization:",
        "bearer ",
    )
    failures += emit(
        "no_cookie_token_localstorage_reading",
        not any(word in combined for word in banned),
        found=[word for word in banned if word in combined],
    )

    random_click_patterns = ("pyautogui", "setcursorpos", "mouse_event", ".click(")
    failures += emit(
        "no_random_coordinate_clicking",
        not any(word in combined for word in random_click_patterns),
        found=[word for word in random_click_patterns if word in combined],
    )

    failures += emit(
        "existing_browser_status_page_tools_still_registered",
        {"browser_status", "browser_current_page", "browser_open_url"}.issubset(specs),
    )

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


def _raises(func: Any) -> bool:
    try:
        func()
    except Exception:
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
