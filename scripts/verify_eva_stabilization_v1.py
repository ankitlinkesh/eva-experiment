from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.agent.executor import ToolExecutionResult
from backend.eva.api.routes import _handle_capability_route, _local_tool_summary
from backend.eva.browser import state as browser_state
from backend.eva.core.fast_commands import maybe_handle_fast_command
from backend.eva.core.fast_responses import maybe_handle_fast_response
from backend.eva.core.intent_router import classify_capability_intent
from backend.eva.core.provenance import answer_provenance_status, remember_answer_provenance
from backend.eva.tools.registry import ToolRegistry


class DryRegistry(ToolRegistry):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[dict[str, Any]] = []

    def run(self, name: str, **kwargs: Any) -> Any:
        self.calls.append({"tool": name, "args": kwargs})
        if name == "code_status":
            return {
                "ok": True,
                "indexed": True,
                "indexed_files": 321,
                "last_indexed_at": "2026-05-29T00:00:00+00:00",
                "index_path": str(ROOT / "backend" / "eva" / "data" / "code_index.json"),
                "secrets_indexed": False,
            }
        if name == "research_status":
            return {
                "ok": True,
                "topic_count": 3,
                "item_count": 9,
                "note_count": 4,
                "session_count": 2,
                "database": str(ROOT / "backend" / "eva" / "data" / "research_knowledge.sqlite3"),
            }
        if name == "browser_status":
            return {
                "ok": True,
                "browser_detected": True,
                "active_window_title": "Example - Google Chrome",
                "known_current_url": None,
                "url": None,
                "source": "unknown",
                "verified": False,
                "stale": True,
                "message": "I can't verify the current Chrome page right now.",
                "open_browser_windows": [{"title": "Example - Google Chrome"}],
            }
        if name == "browser_current_page":
            return {
                "ok": True,
                "browser_detected": True,
                "active_window_title": "Example - Google Chrome",
                "current_title": "Example - Google Chrome",
                "current_url": None,
                "source": "cache",
                "verified": False,
                "stale": True,
                "message": "I can't verify the current Chrome page right now. Last known page was https://example.com/old.",
            }
        if name == "chrome_copy_current_url":
            return {
                "ok": False,
                "error": "current_url_unverified",
                "summary": "I can't verify the current Chrome page right now, so I did not copy a stale URL.",
                "source": "cache",
                "verified": False,
                "stale": True,
            }
        if name == "message.prepare":
            return {"ok": True, "recipient": kwargs.get("recipient"), "message": kwargs.get("message"), "draft_prepared": True}
        if name.startswith("spotify_"):
            return {"ok": True, "message": "Spotify dry run."}
        if name == "chrome_search_site":
            return {"ok": True, "message": f"I opened YouTube and searched for {kwargs.get('query')}. I couldn't safely verify playback yet."}
        return super().run(name, **kwargs)


def emit(case: str, passed: bool, **payload: Any) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=False))
    return 0 if passed else 1


def _is_raw_json(text: str) -> bool:
    clean = str(text or "").lstrip()
    if not clean.startswith(("{", "[")):
        return False
    try:
        json.loads(clean)
    except Exception:
        return False
    return True


def main() -> int:
    failures = 0
    registry = DryRegistry()
    session_context: dict[str, Any] = {}

    for command in ("agent status", "code status", "tools status", "permissions status", "research status", "llm status"):
        reply = maybe_handle_fast_command(command, registry, session_context)
        failures += emit(
            f"{command.replace(' ', '_')}_human_by_default",
            bool(reply and not _is_raw_json(reply[0]) and "{" not in reply[0][:20]),
            reply=reply,
        )

    for command in ("agent status raw", "code status raw", "tools status raw", "permissions status raw", "llm status raw"):
        reply = maybe_handle_fast_command(command, registry, session_context)
        failures += emit(f"{command.replace(' ', '_')}_raw_json", bool(reply and _is_raw_json(reply[0])), reply=reply)

    tools_status = maybe_handle_fast_command("tools status", registry, session_context)
    failures += emit(
        "tools_status_not_os_status",
        bool(tools_status and "tool registry" in tools_status[0].lower() and "laptop is reachable" not in tools_status[0].lower()),
        reply=tools_status,
    )

    permissions = maybe_handle_fast_command("what are your permissions status", registry, session_context)
    failures += emit(
        "permissions_question_routes_permissions",
        bool(permissions and "permission gate" in permissions[0].lower() and "confirm override" in permissions[0].lower()),
        reply=permissions,
    )

    raw_tool = _local_tool_summary([ToolExecutionResult(tool="open_app", ok=True, result={"ok": True, "message": "Done, Chrome is open.", "internal": {"x": 1}})])
    failures += emit(
        "raw_tool_dicts_hidden",
        "{'ok':" not in raw_tool and '"internal"' not in raw_tool and "Done, Chrome is open." in raw_tool,
        summary=raw_tool,
    )

    browser_state.remember_navigation("https://example.com/old", title="Old Example", source="cache", verified=False)
    state = browser_state.current_state()
    failures += emit(
        "browser_state_has_staleness_fields",
        all(key in state for key in ("url", "title", "source", "verified", "stale", "captured_at", "age_seconds", "message")),
        state=state,
    )

    page = maybe_handle_fast_command("what page am I on", registry, session_context)
    copy = maybe_handle_fast_command("copy current URL", registry, session_context)
    failures += emit(
        "what_page_does_not_claim_stale_current",
        bool(page and "can't verify the current Chrome page" in page[0] and "Current browser page:" not in page[0]),
        reply=page,
    )
    failures += emit(
        "copy_current_url_refuses_stale",
        bool(copy and "did not copy a stale URL" in copy[0]),
        reply=copy,
    )

    remember_answer_provenance(session_context, source="planner-answer")
    failures += emit(
        "provenance_truthful_for_direct_llm",
        "direct LLM reasoning" in answer_provenance_status(session_context) and "did not use web search" in answer_provenance_status(session_context),
        reply=answer_provenance_status(session_context),
    )

    chatgpt = classify_capability_intent("ask ChatGPT on my Chrome for money making ideas and summarize the result", session_context)
    chatgpt_reply = _handle_capability_route("ask ChatGPT on my Chrome for money making ideas and summarize the result", chatgpt, session_context, None, "verify")
    failures += emit(
        "chatgpt_in_chrome_not_direct_answer",
        bool(
            chatgpt.get("matched")
            and chatgpt.get("suggested_route") == "chatgpt_in_chrome"
            and chatgpt_reply
            and "don't yet have a verified workflow" in chatgpt_reply[0]
            and "money making ideas" not in chatgpt_reply[0].lower()
        ),
        classification=chatgpt,
        reply=chatgpt_reply,
    )
    if chatgpt_reply:
        remember_answer_provenance(session_context, source=chatgpt_reply[1], tools=[str(chatgpt.get("suggested_route") or "")])
    chatgpt_provenance = answer_provenance_status(session_context)
    failures += emit(
        "chatgpt_unavailable_provenance_honest",
        "did not get an answer from ChatGPT in Chrome" in chatgpt_provenance
        and "workflow is not available" in chatgpt_provenance
        and "Tool used: chatgpt_in_chrome" not in chatgpt_provenance,
        reply=chatgpt_provenance,
    )

    verify_failure = _local_tool_summary(
        [
            ToolExecutionResult(
                tool="verify_browser_target",
                ok=False,
                result={
                    "ok": False,
                    "verified": False,
                    "user_message": "I can't verify the YouTube results because the active Chrome tab is not YouTube. I can reopen the YouTube search if you want.",
                    "internal_error": "active_target_mismatch",
                },
                error=None,
            )
        ]
    )
    failures += emit(
        "verify_browser_target_failure_clean_user_message",
        "verify_browser_target failed: None" not in verify_failure
        and "active Chrome tab is not YouTube" in verify_failure
        and not verify_failure.startswith("Done."),
        reply=verify_failure,
    )

    destructive = classify_capability_intent("delete my downloads", session_context)
    destructive_reply = _handle_capability_route("delete my downloads", destructive, session_context, None, "verify")
    failures += emit(
        "delete_downloads_routes_override_without_deleting",
        bool(destructive.get("matched") and destructive.get("suggested_route") == "destructive_file_request" and destructive_reply and "confirm override" in destructive_reply[0].lower()),
        classification=destructive,
        reply=destructive_reply,
    )

    whatsapp = classify_capability_intent("send a WhatsApp message saying hello to raks", session_context)
    whatsapp_reply = _handle_capability_route("send a WhatsApp message saying hello to raks", whatsapp, session_context, None, "verify")
    failures += emit(
        "whatsapp_message_requires_confirmation",
        bool(whatsapp.get("matched") and whatsapp.get("suggested_route") == "whatsapp_message_prepare" and whatsapp_reply and "requires confirmation" in whatsapp_reply[0].lower() and "manually" not in whatsapp_reply[0].lower()),
        classification=whatsapp,
        reply=whatsapp_reply,
    )

    agent_ping = maybe_handle_fast_command("agent mode: say hello in one sentence", registry, session_context)
    failures += emit(
        "simple_agent_ping_hides_trace",
        agent_ping == ("Hello, Ankit.", "fast-command"),
        reply=agent_ping,
    )

    joke = maybe_handle_fast_command("remember that my name is Batman lmao", registry, session_context)
    cleared = maybe_handle_fast_response("lmao im joking")
    tanglish = maybe_handle_fast_response("hi eva epdi iruka")
    tamil = maybe_handle_fast_response("respond in tamil love")
    failures += emit("fake_name_joke_not_saved", bool(joke and "not changing your name" in joke[0].lower()), reply=joke)
    failures += emit("joke_context_clear_supported", bool(cleared and "Ankit" in cleared[0]), reply=cleared)
    failures += emit("tanglish_prompt_supported", bool(tanglish and ("epdi" in tanglish[0].lower() or "iruken" in tanglish[0].lower())), reply=tanglish)
    failures += emit("tamil_love_language_instruction", bool(tamil and "romantic" not in tamil[0].lower() and "Tamil" in tamil[0]), reply=tamil)

    youtube = classify_capability_intent("play pavazhamalli from youtube", session_context)
    spotify = classify_capability_intent("play pavazhamalli on Spotify", session_context)
    openrouter = classify_capability_intent("test OpenRouter API", session_context)
    failures += emit("youtube_source_routes_youtube", youtube.get("capability") == "browser_agent" and youtube.get("site") == "youtube", result=youtube)
    failures += emit("spotify_source_routes_spotify", spotify.get("capability") == "media_music_control", result=spotify)
    failures += emit("openrouter_still_provider_diagnostics", openrouter.get("capability") == "provider_diagnostics" and openrouter.get("provider") == "openrouter", result=openrouter)

    js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8", errors="replace")
    failures += emit(
        "frontend_hides_tool_and_agent_spam_from_chat",
        "HIDE_AGENT_TRACE_BY_DEFAULT" in js
        and "addMessage(\"eva\", label)" not in js
        and "Result: ${event.tool}" not in js,
    )
    failures += emit(
        "voice_final_only_not_tool_events",
        "speakEva(finalDisplayedReply)" in js
        and "speakEva(label" not in js
        and "speakEva(event.message" not in js
        and "local Windows path" in js
        and "Operating system" in js
        and " executable" in js,
    )

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
