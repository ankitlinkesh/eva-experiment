from __future__ import annotations

import os
import re
from typing import Any

from .planner import PlannedToolCall

DEFAULT_MAX_AGENT_STEPS = 6
DEFAULT_MAX_TOOLS_PER_TASK = 10
DEFAULT_MAX_WEB_SEARCHES_PER_TASK = 4
DEFAULT_MAX_SCREEN_CAPTURES_PER_TASK = 2

POWER_TOOLS = {"guarded_power_action", "system_power"}
DESKTOP_ACTION_TOOLS = {"open_app", "open_folder", "open_url", "web_search", "media_control", "media_key", "lock_laptop", "capture_screen"}
AGENTIC_TRIGGERS = (
    "research",
    "find and summarize",
    "compare",
    "plan this",
    "figure out",
    "do this task",
    "step by step",
    "agent mode:",
    "eva, handle this",
)


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def max_agent_steps() -> int:
    return max(1, env_int("MAX_AGENT_STEPS", DEFAULT_MAX_AGENT_STEPS))


def max_tools_per_task() -> int:
    return max(1, env_int("MAX_TOOLS_PER_TASK", DEFAULT_MAX_TOOLS_PER_TASK))


def max_web_searches_per_task() -> int:
    return max(0, env_int("MAX_WEB_SEARCHES_PER_TASK", DEFAULT_MAX_WEB_SEARCHES_PER_TASK))


def max_screen_captures_per_task() -> int:
    return max(0, env_int("MAX_SCREEN_CAPTURES_PER_TASK", DEFAULT_MAX_SCREEN_CAPTURES_PER_TASK))


def agentic_goal(message: str) -> str:
    clean = message.strip()
    if clean.lower().startswith("agent mode:"):
        return clean.split(":", 1)[1].strip() or clean
    if clean.lower().startswith("eva, handle this"):
        return clean.split("this", 1)[-1].strip(" :") or clean
    return clean


def is_agentic_intent(message: str) -> bool:
    text = " ".join(message.lower().strip().split())
    return any(trigger in text for trigger in AGENTIC_TRIGGERS)


def explicitly_requests_screen(message: str) -> bool:
    text = " ".join(message.lower().strip().split())
    verbs = ("look at", "check", "inspect", "analyze", "analyse", "capture", "see", "view")
    nouns = ("screen", "display", "what is open", "what's open", "error")
    return any(verb in text for verb in verbs) and any(noun in text for noun in nouns)


def tool_signature(call: PlannedToolCall) -> str:
    args = call.args or {}
    if call.tool == "web_search":
        return f"web_search:{str(args.get('query') or '').strip().lower()}"
    if call.tool == "open_app":
        return f"open_app:{str(args.get('app') or args.get('app_name') or '').strip().lower()}"
    if call.tool == "open_folder":
        return f"open_folder:{str(args.get('folder') or args.get('folder_name') or '').strip().lower()}"
    if call.tool in POWER_TOOLS:
        return f"{call.tool}:{str(args.get('action') or '').strip().lower()}"
    return f"{call.tool}:{repr(sorted(args.items()))}"


def describe_tool_observation(tool: str, result: Any) -> str:
    if isinstance(result, dict):
        if tool == "web_search":
            query = result.get("query") or "search"
            count = len(result.get("results") or []) if isinstance(result.get("results"), list) else 0
            if result.get("ok") and result.get("provider") == "tavily":
                return f"web_search observed {count} Tavily results for {query}."
            if result.get("fallback") == "browser":
                return f"web_search opened browser fallback for {query} because Tavily was {result.get('error') or 'unavailable'}."
        if tool == "capture_screen":
            return "capture_screen stored one screenshot for inspection."
    return f"{tool} returned {str(result)[:300]}"


def is_unsupported_capability(message: str) -> bool:
    text = " ".join(message.lower().split())
    unsupported_patterns = (
        r"\bemail\b",
        r"\bsend (a )?message\b",
        r"\bbook\b.*\bcalendar\b",
        r"\bcall\b.*\bphone\b",
    )
    return any(re.search(pattern, text) for pattern in unsupported_patterns)
