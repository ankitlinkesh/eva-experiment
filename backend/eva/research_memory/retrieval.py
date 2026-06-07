from __future__ import annotations

from dataclasses import dataclass, field

from .diversity import rerank_for_diversity
from .models import ResearchMemoryItem, ResearchSearchResult
from .quality import find_duplicate_groups, normalize_tags
from .ranking import compute_combined_retrieval_score, compute_recency_score, explain_ranking_factors
from .store import list_research_items, record_research_recall, search_research_items
from .vector_index import is_vector_search_enabled, search_research_vectors, vector_search_status


@dataclass
class ResearchRetrievalResult:
    query: str
    mode: str
    filters: dict[str, str]
    results: list[ResearchSearchResult] = field(default_factory=list)
    plan_notes: list[str] = field(default_factory=list)


def retrieve_research(
    query: str,
    topic: str | None = None,
    tag: str | None = None,
    source_type: str | None = None,
    limit: int = 5,
) -> ResearchRetrievalResult:
    clean_query = str(query or "").strip()
    safe_limit = max(1, min(20, int(limit or 5)))
    filters = _filters(topic=topic, tag=tag, source_type=source_type)
    lexical = search_research_items(clean_query, limit=max(20, safe_limit * 3), topic=topic, tag=tag, source_type=source_type)
    ranked = rank_research_results(lexical, clean_query, task_context={"filters": filters})
    notes = ["Lexical/local Research Memory search used as the baseline."]
    if is_vector_search_enabled():
        vector = search_research_vectors(clean_query, limit=safe_limit, topic=topic, tag=tag)
        notes.append("Vector search is enabled; lightweight local fallback vector matches were merged when available.")
        if vector.ok and vector.results:
            ranked = _merge_results(ranked, vector.results)
            ranked = rank_research_results(ranked, clean_query, task_context={"filters": filters, "vector_merge": True})
    else:
        notes.append("Vector search is disabled by default.")
    deduped = _mark_and_reduce_duplicates(ranked)
    diverse = rerank_for_diversity(deduped, limit=safe_limit, lambda_param=0.65)
    selected = diverse[:safe_limit]
    if len(selected) > 1:
        for item in selected:
            if "Diversity reranking reduced repeated results." not in item.reason:
                item.reason = f"{item.reason}; Diversity reranking reduced repeated results."
        notes.append("Diversity reranking reduces repeated/near-duplicate results.")
    record_research_recall([item.id for item in selected], clean_query)
    return ResearchRetrievalResult(
        query=clean_query,
        mode="local_hybrid",
        filters=filters,
        results=selected,
        plan_notes=notes,
    )


def explain_retrieval_plan(query: str, topic: str | None = None, tag: str | None = None, source_type: str | None = None) -> str:
    status = vector_search_status()
    filters = _filters(topic=topic, tag=tag, source_type=source_type)
    lines = [
        f"Research Memory retrieval plan for {str(query or '').strip() or 'your query'}:",
        "- Use lexical baseline search across local Research Memory v2.",
        "- Apply topic/tag/source filters before ranking." if filters else "- No topic/tag/source filters requested.",
        "- Boost higher quality_score notes.",
        "- Add small deterministic recency scoring; old notes are not hidden.",
        "- Deprioritize duplicate-like or low-quality notes; exact duplicates may be collapsed in output.",
        "- Apply diversity reranking to reduce repeated/near-duplicate final results.",
        f"- Vector search: {'enabled' if status.enabled else 'disabled'} by default; provider {status.provider}.",
        "No cloud calls, cloud embeddings, Chroma/Qdrant activation, or private page scraping are used in this phase.",
    ]
    return "\n".join(lines)


def rank_research_results(results: list[object], query: str, task_context: object | None = None) -> list[ResearchSearchResult]:
    duplicate_ids = _duplicate_ids()
    ranked: list[ResearchSearchResult] = []
    for result in results:
        search_result = _as_search_result(result, query)
        quality = max(0.0, min(1.0, float(search_result.quality_score or 0.0)))
        warnings = [warning for warning in search_result.quality_warnings if warning != "hash available"]
        recency = compute_recency_score(search_result.created_at)
        duplicate_penalty = 0.0
        if search_result.id in duplicate_ids:
            duplicate_penalty = 1.2
            if "duplicate-like" not in warnings:
                warnings.append("duplicate-like")
        low_quality_penalty = len(warnings) * 0.35
        search_result.score = compute_combined_retrieval_score(
            search_result.score,
            quality_score=quality,
            recency_score=recency,
            duplicate_penalty=duplicate_penalty,
            low_quality_penalty=low_quality_penalty,
        )
        search_result.quality_warnings = warnings or search_result.quality_warnings
        explanation = explain_ranking_factors(
            search_result,
            {
                "quality_score": quality,
                "recency_score": recency,
                "duplicate_penalty": duplicate_penalty,
                "low_quality_penalty": low_quality_penalty,
            },
        )
        search_result.reason = f"{search_result.reason}; {explanation}"
        ranked.append(search_result)
    return sorted(ranked, key=lambda item: item.score, reverse=True)


def format_retrieval_results(result: ResearchRetrievalResult | str, **kwargs: object) -> str:
    retrieval = result if isinstance(result, ResearchRetrievalResult) else retrieve_research(str(result or ""), **kwargs)
    if not retrieval.results:
        return f"Research Memory retrieval results: no local matches found for {retrieval.query or 'your query'}."
    filter_text = _filter_text(retrieval.filters)
    header = f"Research Memory retrieval results for {retrieval.query or 'your query'}{filter_text}:"
    lines = [header, "Research memory mode: local hybrid retrieval."]
    for item in retrieval.results:
        warnings = [warning for warning in item.quality_warnings if warning != "hash available"]
        warning_text = f" Warnings: {', '.join(warnings)}." if warnings else ""
        lines.append(f"- {item.title}: {item.summary}")
        lines.append(f"  Topic: {item.topic}. Type: {item.source_type}. Match: {item.reason}.{warning_text}")
        if item.redacted:
            lines.append("  Redacted: sensitive-looking text was sanitized before storage.")
    return "\n".join(lines)


def retrieval_status() -> str:
    status = vector_search_status()
    return "\n".join(
        [
            "Research Memory hybrid retrieval status:",
            "Mode: local hybrid retrieval planner.",
            "Baseline: lexical baseline search over local Research Memory v2.",
            "Filters: topic, tag, and source type.",
            "Ranking: lexical match plus quality_score boost, small recency boost, duplicate/low-quality penalties, and diversity reranking.",
            f"Vector search: {'enabled' if status.enabled else 'disabled by default'} using {status.provider}.",
            "Cloud calls: none. Raw vectors and database paths are never shown in normal output.",
        ]
    )


def _merge_results(primary: list[ResearchSearchResult], secondary: list[ResearchSearchResult]) -> list[ResearchSearchResult]:
    merged: dict[str, ResearchSearchResult] = {item.id: item for item in primary}
    for item in secondary:
        existing = merged.get(item.id)
        if existing:
            existing.score = max(float(existing.score or 0.0), float(item.score or 0.0) + 1.0)
            if "vector" not in existing.reason.lower():
                existing.reason = f"{existing.reason}; vector fallback match"
        else:
            item.score = float(item.score or 0.0) + 1.0
            merged[item.id] = item
    return list(merged.values())


def _mark_and_reduce_duplicates(results: list[ResearchSearchResult]) -> list[ResearchSearchResult]:
    seen_hashes: set[str] = set()
    output: list[ResearchSearchResult] = []
    for item in results:
        if item.content_hash and item.content_hash in seen_hashes:
            continue
        if item.content_hash:
            seen_hashes.add(item.content_hash)
        output.append(item)
    return output


def _as_search_result(value: object, query: str) -> ResearchSearchResult:
    if isinstance(value, ResearchSearchResult):
        return value
    if isinstance(value, ResearchMemoryItem):
        score = _lexical_score(value, query)
        return ResearchSearchResult(
            id=value.id,
            topic=value.topic,
            title=value.title,
            score=score,
            reason="local item match",
            summary=value.summary,
            source_url=value.source_url,
            source_type=value.source_type,
            created_at=value.created_at,
            redacted=value.redacted,
            tags=value.tags,
            content_hash=value.content_hash,
            quality_score=value.quality_score,
            quality_warnings=value.quality_warnings,
        )
    return ResearchSearchResult(id="", topic="general", title="Unknown", score=0, reason="unrecognized result", summary=str(value)[:300])


def _lexical_score(item: ResearchMemoryItem, query: str) -> float:
    terms = _terms(query)
    haystack = _terms(f"{item.topic} {item.title} {item.summary} {' '.join(item.tags)}")
    return float(len(terms & haystack) or 0)


def _terms(text: str) -> set[str]:
    return {part for part in "".join(ch.lower() if ch.isalnum() else " " for ch in str(text or "")).split() if len(part) > 2}


def _duplicate_ids() -> set[str]:
    exact, near = find_duplicate_groups()
    ids = {str(item.id) for group in exact for item in group}
    ids.update(str(item.id) for pair in near for item in pair[:2])
    return ids


def _filters(topic: str | None = None, tag: str | None = None, source_type: str | None = None) -> dict[str, str]:
    filters: dict[str, str] = {}
    if topic:
        filters["topic"] = str(topic).strip()
    tags = normalize_tags(tag)
    if tags:
        filters["tag"] = tags[0]
    if source_type:
        filters["source"] = str(source_type).strip()
    return filters


def _filter_text(filters: dict[str, str]) -> str:
    if not filters:
        return ""
    return " (" + ", ".join(f"{key}: {value}" for key, value in filters.items()) + ")"


__all__ = [
    "ResearchRetrievalResult",
    "explain_retrieval_plan",
    "format_retrieval_results",
    "rank_research_results",
    "retrieval_status",
    "retrieve_research",
]
