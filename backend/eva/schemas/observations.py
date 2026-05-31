from __future__ import annotations

from dataclasses import asdict, field
from datetime import datetime, timezone
from typing import Any

from .modeling import schema_dataclass

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@schema_dataclass
class EvaObservation:
    action_id: str
    success: bool
    summary: str
    raw_observation: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    local_ref: str | None = None
    created_at: str = field(default_factory=_now)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict

    @classmethod
    def from_existing_agent_observation(cls, observation: Any) -> "EvaObservation":
        return cls(
            action_id=str(getattr(observation, "action_id", "")),
            success=bool(getattr(observation, "success", False)),
            summary=str(getattr(observation, "summary", "")),
            raw_observation=dict(getattr(observation, "raw_observation", {}) or {}),
            error=getattr(observation, "error", None),
            local_ref=getattr(observation, "screenshot_ref", None),
            created_at=str(getattr(observation, "created_at", "") or _now()),
        )


def from_existing_agent_observation(observation: Any) -> EvaObservation:
    return EvaObservation.from_existing_agent_observation(observation)
