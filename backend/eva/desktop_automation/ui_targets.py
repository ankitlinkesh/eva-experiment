from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class UiTarget:
    label: str
    role: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    method: str = "uia"
    app: str | None = None
    window_title: str | None = None
    target_id: str = field(default_factory=lambda: uuid4().hex)
    safety_notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_value(cls, value: Any) -> "UiTarget | None":
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict) or "confidence" not in value or "label" not in value:
            return None
        return cls(
            label=str(value.get("label") or "target"),
            role=str(value.get("role") or "unknown"),
            x=int(value.get("x") or 0),
            y=int(value.get("y") or 0),
            width=max(1, int(value.get("width") or 1)),
            height=max(1, int(value.get("height") or 1)),
            confidence=max(0.0, min(1.0, float(value.get("confidence") or 0.0))),
            method=str(value.get("method") or "unknown"),
            app=str(value.get("app") or "") or None,
            window_title=str(value.get("window_title") or "") or None,
            target_id=str(value.get("target_id") or uuid4().hex),
            safety_notes=[str(item) for item in value.get("safety_notes") or []],
        )
