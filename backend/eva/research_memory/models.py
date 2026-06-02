from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def _as_dict(instance: object) -> dict[str, Any]:
    return asdict(instance)


@dataclass
class ResearchMemoryItem:
    id: str
    topic: str
    title: str
    summary: str
    content_preview: str
    source_type: str
    source_url: str | None = None
    source_domain: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    confidence: str = "medium"
    private: bool = False
    redacted: bool = False
    provenance: str = "research_memory_v2"
    content_hash: str = ""
    quality_score: float = 0.0
    quality_warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return _as_dict(self)


@dataclass
class ResearchSource:
    id: str
    title: str
    url: str | None
    domain: str | None
    source_type: str
    added_at: str
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return _as_dict(self)


@dataclass
class ResearchSearchResult:
    id: str
    topic: str
    title: str
    score: float
    reason: str
    summary: str
    source_url: str | None = None
    source_type: str = "user_note"
    created_at: str = ""
    redacted: bool = False
    tags: list[str] = field(default_factory=list)
    content_hash: str = ""
    quality_score: float = 0.0
    quality_warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return _as_dict(self)


@dataclass
class ResearchMemoryStatus:
    item_count: int
    source_count: int
    topic_count: int
    db_path: str
    last_updated: str | None
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return _as_dict(self)
