from __future__ import annotations

import json
import re

from ..llm.router import get_llm_status
from ..core.persona import CAPABILITY_SUMMARY, USER_PROFILE_SUMMARY
from ..tools.registry import ToolRegistry
from ..tools.tavily_search import tavily_status


GREETINGS = {"hi", "hii", "hiii", "hello", "hey", "yo", "eva"}
APP_WORDS = {
    "calculator",
    "chrome",
    "cmd",
    "codex",
    "discord",
    "edge",
    "explorer",
    "notepad",
    "paint",
    "powershell",
    "settings",
    "spotify",
    "task manager",
    "terminal",
    "vscode",
    "vs code",
    "visual studio code",
    "whatsapp",
    "word",
    "excel",
    "powerpoint",
}
FOLDER_WORDS = {"desktop", "documents", "downloads", "pictures", "videos", "music", "eva", "eva folder"}
WEB_ALIASES = {
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chatgpt.com",
    "spotify web": "https://open.spotify.com",
    "whatsapp web": "https://web.whatsapp.com",
}
ABOUT_ME_COMMANDS = {
    "tell me about myself",
    "about me",
    "what do you know about me",
    "who am i",
    "who am i to you",
    "what do you remember about me",
}
ABOUT_EVA_COMMANDS = {
    "tell me about yourself",
    "who are you",
    "what are you",
    "introduce yourself",
}
EVA_IDENTITY_SUMMARY = (
    "I am Eva, your local desktop agent for this Windows laptop. I can open apps, search, control basic "
    "desktop actions, show screen snapshots only when asked, and respond through local Ollama. I will not "
    "pretend I have calendar, email, or messaging powers until those modules actually exist."
)


def _after_prefix(text: str, prefixes: tuple[str, ...]) -> str | None:
    for prefix in prefixes:
        if text.startswith(prefix):
            value = text[len(prefix):].strip(" :")
            if value:
                return value
    return None


def _format_web_search_result(result: object) -> str:
    if not isinstance(result, dict):
        return str(result)
    query = result.get("query") or "your search"
    if result.get("ok") and result.get("provider") == "tavily":
        lines = [f"I searched Tavily for: {query}."]
        answer = str(result.get("answer") or "").strip()
        if answer:
            lines.append(answer)
        results = result.get("results") or []
        if isinstance(results, list) and results:
            lines.append("Top results:")
            for item in results[:5]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "Untitled")
                url = str(item.get("url") or "")
                lines.append(f"- {title}: {url}" if url else f"- {title}")
        return "\n".join(lines)
    if result.get("fallback") == "browser":
        reason = result.get("error") or "unavailable"
        return f"Tavily search was {reason}, so I opened a browser search for: {query}."
    return str(result)


def _run_tool(tools: ToolRegistry, name: str, **kwargs: object) -> tuple[str, str]:
    try:
        result = tools.run(name, **kwargs)
        if name == "web_search":
            return _format_web_search_result(result), "desktop-tool"
        return str(result), "desktop-tool"
    except Exception as exc:
        return f"I tried, but Windows reported: {exc}", "desktop-tool"


def maybe_handle_fast_command(message: str, tools: ToolRegistry) -> tuple[str, str] | None:
    normalized = " ".join(message.lower().strip().split())
    original = message.strip()
    if not normalized:
        return None

    if normalized in GREETINGS:
        return "I am here. Local command layer is online.", "fast-command"

    if any(command in normalized for command in ABOUT_ME_COMMANDS):
        return USER_PROFILE_SUMMARY, "fast-command"

    if any(command in normalized for command in ABOUT_EVA_COMMANDS):
        return EVA_IDENTITY_SUMMARY, "fast-command"

    if normalized in {"status", "system status", "laptop status", "pc status", "computer status"}:
        status = tools.run("system_status")
        return (
            f"Laptop is reachable. OS: {status['os_name']}. Shell: {status['shell']}.",
            "fast-command",
        )

    if normalized in {"what can you do", "help", "commands", "capabilities"}:
        return CAPABILITY_SUMMARY, "fast-command"

    if normalized in {"llm status", "model status", "cloud status"}:
        status = get_llm_status()
        return json.dumps(status, indent=2), "fast-command"

    if normalized in {"web status", "search status", "tavily status"}:
        status = tavily_status()
        return json.dumps(status, indent=2), "fast-command"

    app = _after_prefix(normalized, ("open app ", "launch app ", "start app ", "open ", "launch ", "start "))
    if app:
        if app in FOLDER_WORDS:
            return _run_tool(tools, "open_folder", folder_name=app)
        if app in WEB_ALIASES:
            return _run_tool(tools, "open_url", url=WEB_ALIASES[app])
        if app in APP_WORDS:
            return _run_tool(tools, "open_app", app_name=app)

    close_target = _after_prefix(normalized, ("close ", "quit ", "kill app ", "exit app "))
    if close_target:
        return _run_tool(tools, "close_app", app_name=close_target)

    folder = _after_prefix(normalized, ("open folder ", "show folder ", "open my ", "show my "))
    if folder or normalized in {f"open {name}" for name in FOLDER_WORDS}:
        folder_name = folder or normalized.removeprefix("open ")
        return _run_tool(tools, "open_folder", folder_name=folder_name)

    url = _after_prefix(original, ("open url ", "open website ", "go to ", "visit "))
    if url:
        return _run_tool(tools, "open_url", url=url)

    if re.match(r"^(open|visit)\s+([a-z0-9-]+\.)+[a-z]{2,}(/.*)?$", normalized):
        target = original.split(maxsplit=1)[1]
        return _run_tool(tools, "open_url", url=target)

    search = _after_prefix(original, ("search for ", "google ", "look up ", "search web for ", "web search "))
    if search:
        return _run_tool(tools, "web_search", query=search)

    if normalized in {"show screen", "capture screen", "view screen", "see my screen", "screen shot", "screenshot"}:
        return "Use Capture screen in the Screen Bay for a one-time screenshot. I do not watch continuously.", "fast-command"

    media_actions = {
        "mute": "mute",
        "unmute": "mute",
        "volume up": "volume_up",
        "increase volume": "volume_up",
        "louder": "louder",
        "volume down": "volume_down",
        "decrease volume": "volume_down",
        "quieter": "quieter",
        "play": "play_pause",
        "pause": "play_pause",
        "play pause": "play_pause",
        "next song": "next",
        "next track": "next",
        "previous song": "previous",
        "previous track": "previous",
    }
    if normalized in media_actions:
        return _run_tool(tools, "media_key", action=media_actions[normalized])

    if normalized in {"lock", "lock laptop", "lock pc", "lock screen"}:
        return _run_tool(tools, "system_power", action="lock")

    confirm_actions = {
        "confirm sleep": "sleep",
        "confirm sleep laptop": "sleep",
        "confirm shutdown": "shutdown",
        "confirm shutdown laptop": "shutdown",
        "confirm turn off laptop": "shutdown",
        "confirm restart": "restart",
        "confirm restart laptop": "restart",
        "confirm sign out": "sign_out",
        "confirm log out": "log_out",
    }
    if normalized in confirm_actions:
        return _run_tool(tools, "system_power", action=confirm_actions[normalized], confirmed=True)


    return None




