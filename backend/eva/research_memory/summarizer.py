from __future__ import annotations

from .models import ResearchMemoryItem, ResearchSearchResult
from .store import list_recent_research, search_research_items


def summarize_items(items: list[ResearchMemoryItem]) -> str:
    if not items:
        return "Research topic not found in local Research Memory v2. No saved local research memory matched yet."
    topic = items[0].topic
    lines = [f"Research memory summary for {topic}:"]
    for item in items[:8]:
        source = f" ({item.source_domain})" if item.source_domain else ""
        flag = " [redacted]" if item.redacted else ""
        created = f" Created: {item.created_at}." if item.created_at else ""
        lines.append(f"- {item.title}{source}{flag}: {item.summary} Type: {item.source_type}.{created}")
    lines.append("Source note: this summary uses locally saved research memory only.")
    return "\n".join(lines)


def summarize_topic(topic: str) -> str:
    results = search_research_items(topic, limit=10)
    items = []
    for result in results:
        if result.topic.lower() == str(topic or "").lower() or str(topic or "").lower() in result.topic.lower():
            from .store import get_research_item

            item = get_research_item(result.id)
            if item:
                items.append(item)
    if not items:
        recent = [item for item in list_recent_research(limit=20) if str(topic or "").lower() in item.topic.lower()]
        items = recent[:10]
    return summarize_items(items)


def summarize_search_results(query: str, results: list[ResearchSearchResult]) -> str:
    if not results:
        return f"Research memory search: no local saved results for {query}."
    lines = [f"Research memory results for {query}:"]
    for result in results[:8]:
        source = f" - {result.source_url}" if result.source_url else ""
        redacted = " Redacted: sensitive-looking text was sanitized before storage." if result.redacted else ""
        created = result.created_at or "unknown"
        lines.append(
            f"- {result.title}: {result.summary}\n"
            f"  Topic: {result.topic}. Type: {result.source_type}. Created: {created}. Match: {result.reason}.{redacted}{source}"
        )
    return "\n".join(lines)
