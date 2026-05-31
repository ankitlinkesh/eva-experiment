from __future__ import annotations

from .store import ResearchStore


def retrieve_research(topic: str, query: str = "", limit: int = 5, store: ResearchStore | None = None) -> dict:
    active_store = store or ResearchStore()
    return {
        "ok": True,
        "topic": topic,
        "query": query,
        "embedding_model": "keyword",
        "rerank_model": "keyword",
        "matches": active_store.recall(topic, query=query, limit=limit),
    }
