from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .config import MAX_NOTE_LENGTH, MAX_SOURCE_TITLE_LENGTH, MAX_SUMMARY_LENGTH, RESEARCH_MEMORY_DB_PATH
from .models import ResearchMemoryItem, ResearchMemoryStatus, ResearchSearchResult
from .quality import content_hash, normalize_tags, quality_score, quality_warnings
from .sources import extract_domain, extract_tags, infer_topic, normalize_source_url, redact_research_text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return uuid4().hex


def _db_path(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else RESEARCH_MEMORY_DB_PATH


def _connect(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = _db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_research_memory_store(path: str | Path | None = None) -> Path:
    db_path = _db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS research_items (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                content_preview TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_url TEXT,
                source_domain TEXT,
                tags_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                confidence TEXT NOT NULL,
                private INTEGER NOT NULL,
                redacted INTEGER NOT NULL,
                provenance TEXT NOT NULL,
                content_hash TEXT NOT NULL DEFAULT '',
                quality_score REAL NOT NULL DEFAULT 0,
                quality_warnings_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS research_sources (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT,
                domain TEXT,
                source_type TEXT NOT NULL,
                added_at TEXT NOT NULL,
                notes TEXT NOT NULL
            );
            """
        )
        _migrate_research_items(db)
    return db_path


def _migrate_research_items(db: sqlite3.Connection) -> None:
    columns = {str(row["name"]) for row in db.execute("PRAGMA table_info(research_items)").fetchall()}
    migrations = {
        "content_hash": "ALTER TABLE research_items ADD COLUMN content_hash TEXT NOT NULL DEFAULT ''",
        "quality_score": "ALTER TABLE research_items ADD COLUMN quality_score REAL NOT NULL DEFAULT 0",
        "quality_warnings_json": "ALTER TABLE research_items ADD COLUMN quality_warnings_json TEXT NOT NULL DEFAULT '[]'",
    }
    for column, statement in migrations.items():
        if column not in columns:
            db.execute(statement)
    rows = db.execute("SELECT * FROM research_items WHERE content_hash='' OR quality_score=0 OR quality_warnings_json='[]'").fetchall()
    for row in rows:
        title = str(row["title"] or "")
        summary = str(row["summary"] or "")
        preview = str(row["content_preview"] or summary)
        hash_value = content_hash(title, preview)
        warnings = quality_warnings(title, preview, hash_value)
        score = quality_score(title, preview, warnings)
        db.execute(
            "UPDATE research_items SET content_hash=?, quality_score=?, quality_warnings_json=? WHERE id=?",
            (hash_value, score, json.dumps(warnings), row["id"]),
        )


def add_research_item(item: ResearchMemoryItem, path: str | Path | None = None) -> ResearchMemoryItem:
    init_research_memory_store(path)
    now = _now()
    item_id = item.id or _id()
    topic = (item.topic or infer_topic(item.summary or item.content_preview or item.title)).strip()[:180] or "general"
    title, title_redacted = redact_research_text(item.title or topic, max_len=MAX_SOURCE_TITLE_LENGTH)
    summary, summary_redacted = redact_research_text(item.summary or item.content_preview or title, max_len=MAX_SUMMARY_LENGTH)
    preview, preview_redacted = redact_research_text(item.content_preview or summary, max_len=MAX_NOTE_LENGTH)
    source_url = normalize_source_url(item.source_url)
    source_domain = item.source_domain or extract_domain(source_url)
    tags = normalize_tags(item.tags) or extract_tags(f"{topic} {title} {summary}")
    redacted = bool(item.redacted or title_redacted or summary_redacted or preview_redacted)
    hash_value = item.content_hash or content_hash(title, preview)
    warnings = item.quality_warnings or quality_warnings(title, preview, hash_value)
    score = item.quality_score or quality_score(title, preview, warnings)
    created_at = item.created_at or now
    updated_at = now
    stored = ResearchMemoryItem(
        id=item_id,
        topic=topic,
        title=title[:MAX_SOURCE_TITLE_LENGTH],
        summary=summary[:MAX_SUMMARY_LENGTH],
        content_preview=preview[:MAX_NOTE_LENGTH],
        source_type=item.source_type or "user_note",
        source_url=source_url,
        source_domain=source_domain,
        tags=tags[:8],
        created_at=created_at,
        updated_at=updated_at,
        confidence=item.confidence or "medium",
        private=bool(item.private),
        redacted=redacted,
        provenance=item.provenance or "research_memory_v2",
        content_hash=hash_value,
        quality_score=score,
        quality_warnings=warnings,
    )
    with _connect(path) as db:
        db.execute(
            """
            INSERT OR REPLACE INTO research_items(
                id, topic, title, summary, content_preview, source_type, source_url, source_domain,
                tags_json, created_at, updated_at, confidence, private, redacted, provenance,
                content_hash, quality_score, quality_warnings_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                stored.id,
                stored.topic,
                stored.title,
                stored.summary,
                stored.content_preview,
                stored.source_type,
                stored.source_url,
                stored.source_domain,
                json.dumps(stored.tags),
                stored.created_at,
                stored.updated_at,
                stored.confidence,
                1 if stored.private else 0,
                1 if stored.redacted else 0,
                stored.provenance,
                stored.content_hash,
                stored.quality_score,
                json.dumps(stored.quality_warnings),
            ),
        )
        if stored.source_url or stored.source_domain:
            db.execute(
                """
                INSERT OR REPLACE INTO research_sources(id, title, url, domain, source_type, added_at, notes)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (stored.id, stored.title, stored.source_url, stored.source_domain, stored.source_type, now, "Saved with research memory item."),
            )
    return stored


def get_research_item(item_id: str, path: str | Path | None = None) -> ResearchMemoryItem | None:
    init_research_memory_store(path)
    with _connect(path) as db:
        row = db.execute("SELECT * FROM research_items WHERE id=?", (str(item_id or ""),)).fetchone()
    return _item(row) if row else None


def list_recent_research(limit: int = 10, path: str | Path | None = None) -> list[ResearchMemoryItem]:
    init_research_memory_store(path)
    safe_limit = max(1, min(50, int(limit or 10)))
    with _connect(path) as db:
        rows = db.execute("SELECT * FROM research_items ORDER BY updated_at DESC LIMIT ?", (safe_limit,)).fetchall()
    return [_item(row) for row in rows]


def list_research_items(topic: str | None = None, limit: int = 1000, path: str | Path | None = None) -> list[ResearchMemoryItem]:
    init_research_memory_store(path)
    safe_limit = max(1, min(5000, int(limit or 1000)))
    clean_topic = str(topic or "").strip()
    with _connect(path) as db:
        if clean_topic:
            rows = db.execute(
                "SELECT * FROM research_items WHERE lower(topic)=lower(?) ORDER BY updated_at DESC LIMIT ?",
                (clean_topic, safe_limit),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM research_items ORDER BY updated_at DESC LIMIT ?", (safe_limit,)).fetchall()
    return [_item(row) for row in rows]


def search_research_items(
    query: str,
    limit: int = 10,
    path: str | Path | None = None,
    *,
    topic: str | None = None,
    tag: str | None = None,
    source_type: str | None = None,
) -> list[ResearchSearchResult]:
    init_research_memory_store(path)
    terms = _terms(query)
    safe_limit = max(1, min(50, int(limit or 10)))
    with _connect(path) as db:
        rows = db.execute("SELECT * FROM research_items ORDER BY updated_at DESC LIMIT 500").fetchall()
    scored: list[ResearchSearchResult] = []
    for row in rows:
        item = _item(row)
        if topic and item.topic.lower() != str(topic).strip().lower():
            continue
        if tag and str(tag).strip().lower() not in {entry.lower() for entry in item.tags}:
            continue
        if source_type and item.source_type.lower() != str(source_type).strip().lower():
            continue
        score, reason = _score(item, terms)
        if score <= 0 and terms:
            continue
        scored.append(
            ResearchSearchResult(
                id=item.id,
                topic=item.topic,
                title=item.title,
                score=score,
                reason=reason,
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
    return sorted(scored, key=lambda result: result.score, reverse=True)[:safe_limit]


def list_topics(limit: int = 50, path: str | Path | None = None) -> list[str]:
    init_research_memory_store(path)
    safe_limit = max(1, min(200, int(limit or 50)))
    with _connect(path) as db:
        rows = db.execute(
            "SELECT topic, MAX(updated_at) AS last_updated FROM research_items GROUP BY topic ORDER BY last_updated DESC LIMIT ?",
            (safe_limit,),
        ).fetchall()
    return [str(row["topic"]) for row in rows]


def research_memory_status(path: str | Path | None = None) -> ResearchMemoryStatus:
    db_path = init_research_memory_store(path)
    with _connect(path) as db:
        item_count = int(db.execute("SELECT COUNT(*) FROM research_items").fetchone()[0])
        source_count = int(db.execute("SELECT COUNT(*) FROM research_sources").fetchone()[0])
        topic_count = int(db.execute("SELECT COUNT(DISTINCT topic) FROM research_items").fetchone()[0])
        last = db.execute("SELECT MAX(updated_at) FROM research_items").fetchone()[0]
    summary = f"Research Memory v2 has {item_count} saved item(s) across {topic_count} topic(s)."
    return ResearchMemoryStatus(item_count=item_count, source_count=source_count, topic_count=topic_count, db_path=str(db_path), last_updated=last, summary=summary)


def count_redacted_items(path: str | Path | None = None) -> int:
    init_research_memory_store(path)
    with _connect(path) as db:
        return int(db.execute("SELECT COUNT(*) FROM research_items WHERE redacted=1").fetchone()[0])


def delete_research_item(item_id: str, path: str | Path | None = None) -> bool:
    init_research_memory_store(path)
    with _connect(path) as db:
        cursor = db.execute("DELETE FROM research_items WHERE id=?", (str(item_id or ""),))
        db.execute("DELETE FROM research_sources WHERE id=?", (str(item_id or ""),))
    return cursor.rowcount > 0


def clear_research_topic(topic: str, path: str | Path | None = None) -> int:
    init_research_memory_store(path)
    clean_topic = str(topic or "").strip()
    if not clean_topic:
        return 0
    with _connect(path) as db:
        rows = db.execute("SELECT id FROM research_items WHERE lower(topic)=lower(?)", (clean_topic,)).fetchall()
        item_ids = [str(row["id"]) for row in rows]
        cursor = db.execute("DELETE FROM research_items WHERE lower(topic)=lower(?)", (clean_topic,))
        for item_id in item_ids:
            db.execute("DELETE FROM research_sources WHERE id=?", (item_id,))
    return int(cursor.rowcount or 0)


def _item(row: sqlite3.Row) -> ResearchMemoryItem:
    try:
        tags = json.loads(row["tags_json"] or "[]")
    except json.JSONDecodeError:
        tags = []
    try:
        warnings = json.loads(row["quality_warnings_json"] or "[]")
    except (IndexError, KeyError, json.JSONDecodeError):
        warnings = []
    return ResearchMemoryItem(
        id=row["id"],
        topic=row["topic"],
        title=row["title"],
        summary=row["summary"],
        content_preview=row["content_preview"],
        source_type=row["source_type"],
        source_url=row["source_url"],
        source_domain=row["source_domain"],
        tags=[str(tag) for tag in tags if str(tag).strip()],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        confidence=row["confidence"],
        private=bool(row["private"]),
        redacted=bool(row["redacted"]),
        provenance=row["provenance"],
        content_hash=str(row["content_hash"] or ""),
        quality_score=float(row["quality_score"] or 0),
        quality_warnings=[str(warning) for warning in warnings if str(warning).strip()],
    )


def _terms(text: str) -> set[str]:
    return {part.lower() for part in "".join(ch if ch.isalnum() else " " for ch in str(text or "")).split() if len(part) > 2}


def _score(item: ResearchMemoryItem, terms: set[str]) -> tuple[float, str]:
    if not terms:
        return 1.0, "recent item"
    title = _terms(item.title)
    topic = _terms(item.topic)
    summary = _terms(item.summary)
    tags = {tag.lower() for tag in item.tags}
    domain = _terms(item.source_domain or "")
    score = 0.0
    reasons: list[str] = []
    if terms & topic:
        score += 4 * len(terms & topic)
        reasons.append("topic match")
    if terms & title:
        score += 3 * len(terms & title)
        reasons.append("title match")
    if terms & tags:
        score += 2 * len(terms & tags)
        reasons.append("tag match")
    if terms & summary:
        score += 1 * len(terms & summary)
        reasons.append("summary match")
    if terms & domain:
        score += 1
        reasons.append("source domain match")
    return score, ", ".join(reasons) or "low lexical match"
