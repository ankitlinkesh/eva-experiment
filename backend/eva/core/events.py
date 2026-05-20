from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class EvaEvent:
    type: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def event(type_: str, message: str, **payload: Any) -> EvaEvent:
    return EvaEvent(type=type_, message=message, payload=payload)
