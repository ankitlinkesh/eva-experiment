from __future__ import annotations

from .search import summarize_research_topic
from .store import get_research_item, list_recent_research, list_topics, research_memory_status, search_research_items
from .summarizer import summarize_search_results


def format_research_memory_status() -> str:
    status = research_memory_status()
    lines = [
        "Research Memory v2 status: local SQLite store is available.",
        f"Saved items: {status.item_count}. Sources: {status.source_count}. Topics: {status.topic_count}.",
        "Storage: local runtime SQLite store.",
    ]
    if status.last_updated:
        lines.append(f"Last updated: {status.last_updated}")
    lines.append("Scope: local summaries and source metadata only; private/logged-in content is refused or redacted.")
    return "\n".join(lines)


def format_recent_research(limit: int = 10) -> str:
    items = list_recent_research(limit=limit)
    if not items:
        return "Recent research memory: no local research notes saved yet."
    lines = ["Recent research memory:"]
    for item in items[:limit]:
        flag = " [redacted]" if item.redacted else ""
        source = f" ({item.source_domain})" if item.source_domain else ""
        lines.append(f"- {item.topic}: {item.title}{source}{flag}")
    return "\n".join(lines)


def format_research_search(
    query: str,
    results: object | None = None,
    *,
    topic: str | None = None,
    tag: str | None = None,
    source_type: str | None = None,
) -> str:
    matches = results if isinstance(results, list) else search_research_items(query, limit=10, topic=topic, tag=tag, source_type=source_type)
    label = str(query or "").strip()
    filters = []
    if topic:
        filters.append(f"topic: {topic}")
    if tag:
        filters.append(f"tag: {tag}")
    if source_type:
        filters.append(f"source: {source_type}")
    if filters:
        label = f"{label} ({', '.join(filters)})"
    return summarize_search_results(label, matches)


def format_research_topic_summary(topic: str) -> str:
    return summarize_research_topic(topic)


def format_research_item_detail(item_id: str) -> str:
    item = get_research_item(item_id)
    if not item:
        return f"Research memory item not found: {item_id}."
    lines = [
        f"Research memory item: {item.title}",
        f"Topic: {item.topic}",
        f"Type: {item.source_type}",
        f"Confidence: {item.confidence}",
        f"Summary: {item.summary}",
    ]
    if item.source_url:
        lines.append(f"Source: {item.source_url}")
    if item.tags:
        lines.append("Tags: " + ", ".join(item.tags))
    if item.redacted:
        lines.append("Note: sensitive text was redacted before storage.")
    return "\n".join(lines)


def format_research_topics(limit: int = 50) -> str:
    topics = list_topics(limit=limit)
    if not topics:
        return "Research topics: no local research memory topics saved yet."
    lines = ["Research topics:"]
    lines.extend(f"- {topic}" for topic in topics)
    return "\n".join(lines)
