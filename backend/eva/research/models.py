from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ResearchTopic:
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResearchItem:
    id: str
    topic_id: str
    title: str
    url: str
    source: str
    snippet: str
    content_summary: str
    raw_content: str
    credibility_note: str
    created_at: str
    updated_at: str

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ResearchNote:
    id: str
    topic_id: str
    note: str
    tags: str
    created_at: str

    def as_dict(self) -> dict:
        return asdict(self)
