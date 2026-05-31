from __future__ import annotations

from .store import ResearchStore


def summarize_research_topic(topic: str, store: ResearchStore | None = None) -> dict:
    active_store = store or ResearchStore()
    return active_store.summarize_topic(topic)
