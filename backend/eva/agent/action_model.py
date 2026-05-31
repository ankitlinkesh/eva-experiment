from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AgentAction:
    tool_name: str
    action_type: str
    description: str
    params: dict[str, Any] = field(default_factory=dict)
    risk_categories: list[str] = field(default_factory=list)
    expected_result: str = ""
    verification: dict[str, Any] = field(default_factory=dict)
    rollback: dict[str, Any] = field(default_factory=dict)
    requires_network: bool = False
    external_visible: bool = False
    destructive: bool = False
    privacy_sensitive: bool = False
    action_id: str = field(default_factory=lambda: uuid4().hex)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentObservation:
    action_id: str
    success: bool
    raw_observation: dict[str, Any]
    summary: str
    error: str | None = None
    screenshot_ref: str | None = None
    created_at: str = field(default_factory=_now)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    action_id: str
    verified: bool
    confidence: float
    evidence: str
    failure_reason: str | None = None
    suggested_repair: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RollbackResult:
    action_id: str
    attempted: bool
    success: bool
    summary: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
