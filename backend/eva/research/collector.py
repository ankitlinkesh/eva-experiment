from __future__ import annotations

from typing import Any

from ..tools.tavily_search import tavily_search_sync


def collect_web_sources(query: str, max_results: int = 5) -> dict[str, Any]:
    clean = query.strip()
    if not clean:
        return {"ok": False, "provider": "tavily", "query": query, "error": "empty_query", "results": []}
    return tavily_search_sync(clean, max_results=max_results)
