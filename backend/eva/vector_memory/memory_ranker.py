from __future__ import annotations

from .base import VectorSearchResult


def rank_memory_results(results: list[VectorSearchResult] | list[dict], task_context: dict | None = None) -> list[VectorSearchResult] | list[dict]:
    def score(item: VectorSearchResult | dict) -> float:
        if isinstance(item, VectorSearchResult):
            return item.score
        return float(item.get("score", 0.0))

    return sorted(results, key=score, reverse=True)
