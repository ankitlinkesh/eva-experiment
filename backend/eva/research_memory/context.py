from __future__ import annotations

import re
from typing import Any

from .retrieval import retrieve_research


CONTEXT_MARKERS = (
    "my saved research",
    "research memory",
    "what i saved",
    "what did i save",
    "saved notes",
    "my notes",
    "what do i have on",
    "use my eva research",
    "retrieve from research memory",
    "saved research",
)

QUERY_STOPWORDS = {
    "about",
    "all",
    "and",
    "answer",
    "explain",
    "for",
    "from",
    "local",
    "memory",
    "my",
    "note",
    "notes",
    "on",
    "research",
    "saved",
    "summarize",
    "summarise",
    "the",
    "to",
    "use",
    "using",
    "what",
}


def should_use_research_memory_context(user_request: str) -> bool:
    text = _normalize(user_request)
    if text in {"research memory status", "research memory retrieval status", "research memory vector status"}:
        return False
    return any(marker in text for marker in CONTEXT_MARKERS) or bool(re.search(r"\bwhat (?:did|do) i save about\b", text))


def build_research_context_for_request(user_request: str, limit: int = 3) -> list[dict[str, Any]]:
    if not should_use_research_memory_context(user_request):
        return []
    if _is_full_dump_request(user_request):
        return [
            {
                "kind": "research_memory_redirect",
                "title": "Full dump refused",
                "summary": "I did not dump all research memory. Use `research memory search <query>`, `research memory export`, or `research memory topics` instead.",
                "topic": "Research Memory",
                "tags": ["safety"],
                "source_type": "local_policy",
                "match": "full dump request redirected",
                "quality_warnings": [],
            }
        ]
    query = _context_query(user_request)
    try:
        retrieval = retrieve_research(query, limit=max(1, min(5, int(limit or 3))))
    except Exception as exc:
        return [
            {
                "kind": "research_memory_unavailable",
                "title": "Research Memory unavailable",
                "summary": f"Local Research Memory context could not be retrieved safely: {str(exc)[:140]}.",
                "topic": "Research Memory",
                "tags": [],
                "source_type": "local_status",
                "match": "unavailable",
                "quality_warnings": [],
            }
        ]
    if not retrieval.results:
        return [
            {
                "kind": "research_memory_empty",
                "title": "No matching saved research found",
                "summary": "No matching saved research found.",
                "topic": "Research Memory",
                "tags": [],
                "source_type": "local_status",
                "match": "no local matches",
                "quality_warnings": [],
            }
        ]
    context: list[dict[str, Any]] = []
    for item in retrieval.results[: max(1, min(5, int(limit or 3)))]:
        warnings = [warning for warning in item.quality_warnings if warning != "hash available"]
        context.append(
            {
                "kind": "research_memory_item",
                "title": item.title[:160],
                "summary": item.summary[:360],
                "topic": item.topic,
                "tags": item.tags[:5],
                "source_type": item.source_type,
                "created_at": item.created_at,
                "match": item.reason,
                "quality_warnings": warnings,
            }
        )
    return context


def format_research_context_for_state(context: list[dict[str, Any]] | None) -> str:
    items = context or []
    if not items:
        return ""
    lines = ["Relevant local research memory:"]
    for index, item in enumerate(items[:5], start=1):
        title = str(item.get("title") or "Saved research").strip()
        summary = str(item.get("summary") or "").strip()
        topic = str(item.get("topic") or "Research Memory").strip()
        tags = item.get("tags") if isinstance(item.get("tags"), list) else []
        tag_text = ", ".join(str(tag) for tag in tags[:5]) if tags else "none"
        match = str(item.get("match") or "local retrieval").strip()
        source_type = str(item.get("source_type") or "local_note").strip()
        warnings = item.get("quality_warnings") if isinstance(item.get("quality_warnings"), list) else []
        warning_text = f", warnings: {', '.join(str(w) for w in warnings)}" if warnings else ""
        if item.get("kind") == "research_memory_empty":
            lines.append("No matching saved research found.")
            continue
        lines.append(f"{index}. {title}: {summary} - topic: {topic}, tags: {tag_text}, source: {source_type}, match: {match}{warning_text}")
    return "\n".join(lines)


def _context_query(user_request: str) -> str:
    text = str(user_request or "").strip()
    cleaned = re.sub(r"^\s*eva v2 (?:plan|dry run|route|execute|run)\s+", "", text, flags=re.IGNORECASE)
    scaffolding = (
        "retrieve from research memory",
        "what did i save about",
        "what i saved about",
        "what do i have on",
        "use my eva research",
        "my saved research",
        "research memory",
        "saved research",
        "saved notes",
        "my notes",
        "use my",
        "local",
        "my",
    )
    for phrase in scaffolding:
        cleaned = re.sub(rf"\b{re.escape(phrase)}\b", " ", cleaned, flags=re.IGNORECASE)
    tokens = [part for part in re.findall(r"[A-Za-z0-9]+", cleaned) if len(part) > 2 and part.lower() not in QUERY_STOPWORDS]
    return " ".join(tokens) or "research"


def _is_full_dump_request(user_request: str) -> bool:
    text = _normalize(user_request)
    return "dump all" in text and "research memory" in text


def _normalize(text: str) -> str:
    return " ".join(str(text or "").lower().strip().split())


__all__ = ["build_research_context_for_request", "format_research_context_for_state", "should_use_research_memory_context"]
