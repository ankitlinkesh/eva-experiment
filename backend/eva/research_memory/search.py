from __future__ import annotations

from .models import ResearchSearchResult
from .store import search_research_items
from .summarizer import summarize_search_results, summarize_topic


def search_research_memory(query: str, limit: int = 10) -> list[ResearchSearchResult]:
    return search_research_items(query, limit=limit)


def summarize_research_topic(topic: str, limit: int = 10) -> str:
    return summarize_topic(topic)


def find_related_research(text: str, limit: int = 5) -> list[ResearchSearchResult]:
    return search_research_items(text, limit=limit)


def summarize_research_search(query: str, limit: int = 10) -> str:
    return summarize_search_results(query, search_research_items(query, limit=limit))
