from __future__ import annotations

from typing import Any


PROVENANCE_LABELS = {
    "direct_llm": "direct LLM reasoning",
    "tavily_search": "Tavily web search",
    "browser_page": "the current browser page",
    "chrome_web_app": "a Chrome web-app action",
    "chatgpt_in_chrome_attempted_unavailable": "an unavailable ChatGPT-in-Chrome workflow",
    "chatgpt_in_chrome_opened_only": "ChatGPT opened in Chrome",
    "chatgpt_in_chrome_completed": "ChatGPT in Chrome",
    "research_sqlite": "local Research SQLite",
    "screen_vision": "screen vision",
    "code_workspace": "local workspace/code tools",
    "tool_result": "local tool result",
    "fast_local": "local deterministic Eva logic",
    "no_answer_generated": "no generated answer",
}


def provenance_from_source(source: str, tools: list[str] | None = None) -> str:
    source_text = str(source or "").lower()
    tool_names = [str(item or "").lower() for item in (tools or [])]
    joined = " ".join([source_text, *tool_names])
    if "chatgpt_in_chrome_completed" in joined:
        return "chatgpt_in_chrome_completed"
    if "chatgpt_in_chrome_opened_only" in joined:
        return "chatgpt_in_chrome_opened_only"
    if "chatgpt_in_chrome_unavailable" in joined or ("chatgpt_in_chrome" in joined and "not_executed" in joined):
        return "chatgpt_in_chrome_attempted_unavailable"
    if "no_answer_generated" in joined:
        return "no_answer_generated"
    if "chatgpt_in_chrome" in joined:
        return "chatgpt_in_chrome_attempted_unavailable"
    if "tavily" in joined or "web_search" in joined:
        return "tavily_search"
    if "browser" in joined or "chrome" in joined:
        return "browser_page" if "current_page" in joined or "summarize_page" in joined else "chrome_web_app"
    if "research" in joined:
        return "research_sqlite"
    if "screen" in joined or "vision" in joined or "analyze_screen" in joined:
        return "screen_vision"
    if "workspace" in joined or "code" in joined:
        return "code_workspace"
    if "tool" in joined or "operator" in joined:
        return "tool_result"
    if "planner-answer" in joined or "fallback" in joined or "provider" in joined or "ollama" in joined or "gemini" in joined:
        return "direct_llm"
    return "fast_local"


def remember_answer_provenance(
    session_context: dict[str, Any] | None,
    *,
    source: str,
    tools: list[str] | None = None,
    detail: str = "",
) -> None:
    if not isinstance(session_context, dict):
        return
    provenance = provenance_from_source(source, tools)
    session_context["last_answer_provenance"] = {
        "provenance": provenance,
        "label": PROVENANCE_LABELS.get(provenance, provenance),
        "source": source,
        "tools": list(tools or []),
        "detail": detail,
    }


def answer_provenance_status(session_context: dict[str, Any] | None) -> str:
    if not isinstance(session_context, dict) or not session_context.get("last_answer_provenance"):
        return "I do not have a recorded source for the previous answer in this session yet."
    item = session_context["last_answer_provenance"]
    provenance = str(item.get("provenance") or "unknown")
    label = str(item.get("label") or PROVENANCE_LABELS.get(provenance, provenance))
    tools = [str(tool) for tool in item.get("tools") or [] if str(tool).strip()]
    source = str(item.get("source") or "").strip()
    if provenance == "chatgpt_in_chrome_attempted_unavailable":
        return "I did not get an answer from ChatGPT in Chrome. I reported that the workflow is not available or reliable yet."
    if provenance == "chatgpt_in_chrome_opened_only":
        return "I opened ChatGPT, but I did not use it to generate that answer."
    if provenance == "chatgpt_in_chrome_completed":
        return "That answer came from ChatGPT in Chrome. I submitted the prompt and read the visible response."
    if provenance == "no_answer_generated":
        return "I did not generate an answer for that request; I only reported that the requested workflow could not run."
    if tools:
        return f"That answer came from {label}. Tool used: {', '.join(tools)}."
    if provenance == "direct_llm":
        return "That answer came from my direct LLM reasoning. I did not use web search, browser reading, or ChatGPT in Chrome for it."
    if source:
        return f"That answer came from {label}. Internal route: {source}."
    return f"That answer came from {label}."
