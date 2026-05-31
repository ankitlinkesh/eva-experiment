from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VectorMemoryItem:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "local"
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: str = field(default_factory=_now)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VectorSearchResult:
    id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
