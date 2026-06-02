from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .embeddings import EmbeddingProviderStatus, get_embedding_provider
from .models import ResearchSearchResult
from .quality import normalize_tags
from .store import _connect, init_research_memory_store, list_research_items


VECTOR_FLAG = "EVA_RESEARCH_MEMORY_VECTOR_ENABLED"


@dataclass
class VectorSearchStatus:
    enabled: bool
    provider: str
    embedding_dim: int
    indexable_item_count: int
    indexed_item_count: int
    backend: str
    message: str


@dataclass
class VectorIndexResult:
    ok: bool
    provider: str
    indexed_count: int
    skipped_count: int
    message: str


@dataclass
class ResearchVectorSearchResult:
    ok: bool
    query: str
    provider: str
    message: str
    results: list[ResearchSearchResult] = field(default_factory=list)


def is_vector_search_enabled() -> bool:
    return str(os.environ.get(VECTOR_FLAG, "")).strip().lower() in {"1", "true", "yes", "on"}


def get_embedding_provider_status() -> EmbeddingProviderStatus:
    return get_embedding_provider().status()


def estimate_indexable_items() -> int:
    return len([item for item in list_research_items(limit=5000) if not item.private and item.summary.strip()])


def vector_search_status() -> VectorSearchStatus:
    provider = get_embedding_provider_status()
    enabled = is_vector_search_enabled()
    indexed = _indexed_item_count()
    indexable = estimate_indexable_items()
    if enabled:
        message = (
            "Research Memory vector search is enabled with a lightweight local fallback provider. "
            "No cloud embeddings are called, and raw vectors are not shown in normal output."
        )
    else:
        message = (
            "Research Memory vector search is disabled by default. "
            "Lexical Research Memory search remains active; future Chroma/Qdrant backends can plug into this local interface."
        )
    return VectorSearchStatus(
        enabled=enabled,
        provider=provider.provider,
        embedding_dim=provider.embedding_dim,
        indexable_item_count=indexable,
        indexed_item_count=indexed,
        backend="local fallback",
        message=message,
    )


def build_research_vector_index(limit: int | None = None, force: bool = False) -> VectorIndexResult:
    provider = get_embedding_provider()
    if not is_vector_search_enabled() and not force:
        return VectorIndexResult(
            ok=False,
            provider=provider.name,
            indexed_count=0,
            skipped_count=estimate_indexable_items(),
            message="Research Memory vector indexing is disabled by default. Use lexical search unless the local vector flag is explicitly enabled.",
        )
    init_research_memory_store()
    _ensure_vector_table()
    safe_limit = max(1, min(5000, int(limit or 5000)))
    items = [item for item in list_research_items(limit=safe_limit) if not item.private and item.summary.strip()]
    indexed = 0
    skipped = 0
    now = _now()
    with _connect() as db:
        for item in items:
            existing = db.execute(
                "SELECT content_hash, provider FROM research_memory_vectors WHERE item_id=?",
                (item.id,),
            ).fetchone()
            if existing and str(existing["content_hash"]) == item.content_hash and str(existing["provider"]) == provider.name and not force:
                skipped += 1
                continue
            vector = provider.embed(f"{item.title}\n{item.summary}\n{' '.join(item.tags)}")
            db.execute(
                """
                INSERT OR REPLACE INTO research_memory_vectors(
                    item_id, provider, embedding_dim, content_hash, vector_json, indexed_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (item.id, provider.name, provider.embedding_dim, item.content_hash, json.dumps(vector), now),
            )
            indexed += 1
    return VectorIndexResult(
        ok=True,
        provider=provider.name,
        indexed_count=indexed,
        skipped_count=skipped,
        message=f"Indexed {indexed} Research Memory item(s) with the lightweight local fallback provider. No cloud embedding calls were made.",
    )


def search_research_vectors(query: str, limit: int = 5, topic: str | None = None, tag: str | None = None) -> ResearchVectorSearchResult:
    provider = get_embedding_provider()
    clean_query = str(query or "").strip()
    if not is_vector_search_enabled():
        return ResearchVectorSearchResult(
            ok=False,
            query=clean_query,
            provider=provider.name,
            message=f"Research Memory vector search is disabled by default. Use lexical search instead: `research memory search {clean_query}`.",
            results=[],
        )
    if _indexed_item_count() == 0:
        build_research_vector_index(force=True)
    query_vector = provider.embed(clean_query)
    tag_filter = normalize_tags(tag)
    safe_limit = max(1, min(20, int(limit or 5)))
    rows = _vector_rows()
    items = {item.id: item for item in list_research_items(limit=5000)}
    scored: list[ResearchSearchResult] = []
    for row in rows:
        item = items.get(str(row["item_id"]))
        if not item:
            continue
        if topic and item.topic.lower() != str(topic).strip().lower():
            continue
        if tag_filter and tag_filter[0] not in {entry.lower() for entry in item.tags}:
            continue
        try:
            vector = [float(value) for value in json.loads(row["vector_json"] or "[]")]
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        score = _cosine(query_vector, vector)
        if score <= 0:
            continue
        scored.append(
            ResearchSearchResult(
                id=item.id,
                topic=item.topic,
                title=item.title,
                score=round(score, 4),
                reason="lightweight local fallback vector match",
                summary=item.summary,
                source_url=item.source_url,
                source_type=item.source_type,
                created_at=item.created_at,
                redacted=item.redacted,
                tags=item.tags,
                content_hash=item.content_hash,
                quality_score=item.quality_score,
                quality_warnings=item.quality_warnings,
            )
        )
    results = sorted(scored, key=lambda item: item.score, reverse=True)[:safe_limit]
    return ResearchVectorSearchResult(
        ok=True,
        query=clean_query,
        provider=provider.name,
        message="Research Memory vector search used the lightweight local fallback provider. This is local-only and not high-quality production semantic search.",
        results=results,
    )


def format_vector_status() -> str:
    status = vector_search_status()
    enabled = "enabled" if status.enabled else "disabled"
    return "\n".join(
        [
            "Research Memory vector search",
            "",
            f"Status: {enabled}.",
            f"Provider: {status.provider} ({status.embedding_dim} dimensions).",
            f"Backend: {status.backend}; future Chroma/Qdrant compatible.",
            f"Indexable items: {status.indexable_item_count}.",
            f"Indexed items: {status.indexed_item_count}.",
            status.message,
        ]
    )


def format_vector_index_preview() -> str:
    status = vector_search_status()
    lines = [
        "Research Memory vector index preview",
        "",
        f"Provider: {status.provider}.",
        f"Would index: {status.indexable_item_count} item(s).",
        f"Already indexed: {status.indexed_item_count} item(s).",
    ]
    if not status.enabled:
        lines.append("Indexing is disabled by default, so no vector index was built.")
    else:
        lines.append("Vector indexing is enabled; use this preview before building or refreshing the local fallback index.")
    return "\n".join(lines)


def format_vector_search(query: str, *, topic: str | None = None, tag: str | None = None) -> str:
    result = search_research_vectors(query, topic=topic, tag=tag)
    if not result.ok:
        return "\n".join(["Research Memory vector search", "", "Status: disabled by default.", result.message])
    if not result.results:
        return "Research Memory vector results: no local vector matches found. Lexical search may still find notes."
    lines = [
        f"Research Memory vector results for {result.query}:",
        "Provider: lightweight local fallback. No cloud embedding calls were made.",
    ]
    for item in result.results:
        lines.append(f"- {item.title}: {item.summary}")
        lines.append(f"  Topic: {item.topic}. Type: {item.source_type}. Match: {item.reason}.")
        if item.redacted:
            lines.append("  Redacted: sensitive-looking text was sanitized before storage.")
    return "\n".join(lines)


def _ensure_vector_table() -> None:
    init_research_memory_store()
    with _connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS research_memory_vectors (
                item_id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                embedding_dim INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                indexed_at TEXT NOT NULL
            )
            """
        )


def _indexed_item_count() -> int:
    try:
        _ensure_vector_table()
        with _connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM research_memory_vectors").fetchone()[0])
    except sqlite3.Error:
        return 0


def _vector_rows() -> list[sqlite3.Row]:
    _ensure_vector_table()
    with _connect() as db:
        return db.execute("SELECT * FROM research_memory_vectors").fetchall()


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "ResearchVectorSearchResult",
    "VectorIndexResult",
    "VectorSearchStatus",
    "build_research_vector_index",
    "estimate_indexable_items",
    "format_vector_index_preview",
    "format_vector_search",
    "format_vector_status",
    "get_embedding_provider_status",
    "is_vector_search_enabled",
    "search_research_vectors",
    "vector_search_status",
]
