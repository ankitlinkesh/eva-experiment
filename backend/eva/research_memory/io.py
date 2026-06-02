from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import RESEARCH_MEMORY_DB_PATH
from .models import ResearchMemoryItem
from .quality import normalize_tags
from .sources import extract_tags, looks_private_or_sensitive, redact_research_text
from .store import add_research_item, clear_research_topic, count_redacted_items, delete_research_item, get_research_item, list_recent_research, list_research_items, list_topics, research_memory_status


@dataclass
class ResearchExportResult:
    filename: str
    item_count: int
    topic: str | None = None


def export_research_memory(topic: str | None = None) -> ResearchExportResult:
    items = list_research_items(topic=topic, limit=5000)
    export_dir = _export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    topic_slug = _slug(topic) if topic else "all"
    filename = f"research_memory_{topic_slug}_{stamp}.json"
    payload = {
        "schema": "eva_research_memory_v2_export",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "topic": topic,
        "item_count": len(items),
        "items": [_export_item(item) for item in items],
    }
    (export_dir / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return ResearchExportResult(filename=filename, item_count=len(items), topic=topic)


def import_research_note(topic: str, title: str, text: str, tags: object | None = None) -> ResearchMemoryItem:
    clean_topic = str(topic or "").strip()
    clean_title = str(title or "").strip() or clean_topic
    clean_text = str(text or "").strip()
    redacted_text, was_text_redacted = redact_research_text(clean_text)
    redacted_title, was_title_redacted = redact_research_text(clean_title)
    return add_research_item(
        ResearchMemoryItem(
            id="",
            topic=clean_topic,
            title=redacted_title or clean_topic,
            summary=redacted_text[:1500],
            content_preview=redacted_text,
            source_type="imported_note",
            tags=normalize_tags(tags) or extract_tags(f"{clean_topic} {clean_title} {clean_text}"),
            confidence="medium",
            private=looks_private_or_sensitive(clean_text),
            redacted=bool(was_text_redacted or was_title_redacted),
            provenance="fast_command:research_memory_import",
        )
    )


def delete_research_memory_item(item_id: str) -> tuple[bool, str]:
    clean_id = str(item_id or "").strip()
    if not clean_id:
        return False, "Research memory delete item needs an exact item id."
    item = get_research_item(clean_id)
    if not item:
        return False, f"Research memory item not found: {clean_id}. Nothing was deleted."
    deleted = delete_research_item(clean_id)
    if not deleted:
        return False, f"Research memory item not found: {clean_id}. Nothing was deleted."
    return True, f"Deleted research memory item {clean_id} from topic {item.topic}."


def clear_research_memory_topic(topic: str, *, confirmed: bool) -> str:
    clean_topic = str(topic or "").strip()
    if not clean_topic:
        return "Research memory clear topic needs a topic name."
    if clean_topic.lower() in {"all", "*", "everything"}:
        return "Research memory clear all is not supported in this phase. No research memory was cleared."
    if not confirmed:
        return f"I did not clear topic {clean_topic}. To clear only this topic, say `research memory clear topic {clean_topic} confirm`."
    deleted = clear_research_topic(clean_topic)
    if deleted <= 0:
        return f"Research memory topic not found: {clean_topic}. Nothing was cleared."
    return f"Cleared research memory topic {clean_topic}. Deleted {deleted} item(s). Other topics were left untouched."


def format_research_memory_stats() -> str:
    status = research_memory_status()
    redacted = count_redacted_items()
    recent_count = len(list_recent_research(limit=10))
    return "\n".join(
        [
            "Research Memory v2 stats:",
            f"Total items: {status.item_count}.",
            f"Topics: {status.topic_count}.",
            f"Redacted items: {redacted}.",
            f"Recent items shown by default: {recent_count}.",
            "Storage: local runtime SQLite store.",
        ]
    )


def format_export_result(result: ResearchExportResult) -> str:
    if result.topic:
        return f"Exported research memory topic {result.topic}: {result.item_count} item(s) to {result.filename}."
    return f"Exported research memory: {result.item_count} item(s) to {result.filename}."


def format_import_result(item: ResearchMemoryItem) -> str:
    suffix = " Sensitive-looking text was redacted before storage." if item.redacted else ""
    return f"Imported research note locally under {item.topic}. Item: {item.id}.{suffix}"


def _export_dir() -> Path:
    return RESEARCH_MEMORY_DB_PATH.parent / "exports"


def _slug(value: str | None) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return text[:60] or "topic"


def _export_item(item: ResearchMemoryItem) -> dict[str, object]:
    return {
        "id": item.id,
        "topic": item.topic,
        "title": item.title,
        "summary": item.summary,
        "content_preview": item.content_preview,
        "source_type": item.source_type,
        "source_url": item.source_url,
        "source_domain": item.source_domain,
        "tags": item.tags,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "confidence": item.confidence,
        "redacted": item.redacted,
        "provenance": item.provenance,
        "content_hash": item.content_hash,
        "quality_score": item.quality_score,
        "quality_warnings": item.quality_warnings,
    }
