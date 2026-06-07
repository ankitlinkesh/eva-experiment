from __future__ import annotations

from datetime import datetime, timezone


def compute_recency_score(created_at: str | None) -> float:
    if not created_at:
        return 0.5
    try:
        parsed = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return 0.5
    age_days = max(0.0, (datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)).total_seconds() / 86400)
    if age_days <= 7:
        return 0.9
    if age_days <= 30:
        return 0.8
    if age_days <= 180:
        return 0.65
    if age_days <= 365:
        return 0.55
    return 0.5


def compute_combined_retrieval_score(
    base_score: float,
    quality_score: float | None = None,
    recency_score: float | None = None,
    duplicate_penalty: float = 0.0,
    low_quality_penalty: float = 0.0,
) -> float:
    base = max(0.0, float(base_score or 0.0))
    quality = max(0.0, min(1.0, float(quality_score if quality_score is not None else 0.5)))
    recency = max(0.0, min(1.0, float(recency_score if recency_score is not None else 0.5)))
    score = base + (quality * 2.5) + (recency * 0.6)
    score -= max(0.0, float(duplicate_penalty or 0.0))
    score -= max(0.0, float(low_quality_penalty or 0.0))
    return round(max(0.0, score), 4)


def explain_ranking_factors(item: object, score_info: dict[str, float] | None = None) -> str:
    info = score_info or {}
    warnings = [warning for warning in getattr(item, "quality_warnings", []) if warning != "hash available"]
    parts = ["Matched query terms."]
    if float(info.get("quality_score", getattr(item, "quality_score", 0.0)) or 0.0) >= 0.7:
        parts.append("Boosted by quality score.")
    if float(info.get("recency_score", 0.5) or 0.5) > 0.65:
        parts.append("Small recency boost.")
    if float(info.get("duplicate_penalty", 0.0) or 0.0) > 0:
        parts.append("Deprioritized because it looks duplicate-like.")
    if warnings or float(info.get("low_quality_penalty", 0.0) or 0.0) > 0:
        parts.append("Deprioritized because quality warnings exist.")
    if bool(info.get("diversity_reranked")):
        parts.append("Diversity reranking reduced repeated results.")
    return " ".join(parts)


def compute_promotion_score(item: object, recall_stats: object | None = None) -> float:
    quality = max(0.0, min(1.0, float(getattr(item, "quality_score", 0.0) or 0.0)))
    warnings = [warning for warning in getattr(item, "quality_warnings", []) if warning != "hash available"]
    recall_count = float(getattr(recall_stats, "recall_count", 0) or 0)
    score = (quality * 6.0) + min(3.0, recall_count * 0.75) + (compute_recency_score(getattr(item, "created_at", None)) * 1.0)
    score -= min(2.0, len(warnings) * 0.5)
    return round(max(0.0, score), 3)


def format_ranking_status() -> str:
    from .vector_index import vector_search_status

    vector = vector_search_status()
    return "\n".join(
        [
            "Research Memory ranking status",
            "",
            "Primary retrieval: lexical-first local Research Memory search.",
            "Quality: quality_score is used as a medium boost.",
            "Recency: recent notes receive a small boost; old notes are not hidden.",
            "Penalties: duplicate-like and low-quality notes are deprioritized, not deleted.",
            "Diversity: Diversity reranking reduces repeated/near-duplicate results.",
            f"Vector search: {'enabled' if vector.enabled else 'disabled by default'}; lexical search remains primary.",
            "Scope: local, deterministic, dependency-free ranking. No cloud embeddings or summarization.",
        ]
    )


def format_memory_review() -> str:
    from .quality import find_duplicate_groups, low_quality_items
    from .store import list_research_items

    items = list_research_items(limit=5000)
    exact, near = find_duplicate_groups()
    low_quality = low_quality_items()
    lines = [
        "Research Memory review",
        "",
        f"Total items: {len(items)}.",
        f"Low-quality notes: {len(low_quality)}.",
        f"Duplicate-like groups: {len(exact) + len(near)}.",
        "",
        format_recall_stats(limit=5),
        "",
        format_promotion_candidates(limit=5),
        "",
        "Suggested safe next commands:",
        "- research memory quality",
        "- research memory duplicates",
        "- research memory promote candidates",
        "- research memory export",
    ]
    return "\n".join(lines)


def format_promotion_candidates(limit: int = 10) -> str:
    from .store import get_recall_stats, list_research_items

    items = list_research_items(limit=5000)
    scored = [
        (compute_promotion_score(item, get_recall_stats(item.id)), item, get_recall_stats(item.id))
        for item in items
    ]
    scored.sort(key=lambda entry: entry[0], reverse=True)
    safe_limit = max(1, min(25, int(limit or 10)))
    if not scored:
        return "Research Memory promotion candidates: no saved notes yet. Preview only. No notes were promoted."
    lines = [
        "Research Memory promotion candidates",
        "",
        "Preview only. No notes were promoted, deleted, or rewritten.",
    ]
    for score, item, stats in scored[:safe_limit]:
        lines.append(f"- {item.title} [{item.topic}] score {score:.2f}; recalled {stats.recall_count} time(s)")
    return "\n".join(lines)


def format_recall_stats(limit: int = 10) -> str:
    from .store import get_top_recalled_items

    recalled = get_top_recalled_items(limit=limit)
    if not recalled:
        return "Research Memory recall stats: no recalled research items yet."
    lines = ["Research Memory recall stats", "", "Most recalled saved research items:"]
    for entry in recalled:
        last = f"; last recalled {entry.last_recalled_at}" if entry.last_recalled_at else ""
        lines.append(f"- {entry.title} [{entry.topic}]: {entry.recall_count} recall(s){last}")
    lines.append("Raw query strings are not stored or shown; only hashed query references are kept locally.")
    return "\n".join(lines)
