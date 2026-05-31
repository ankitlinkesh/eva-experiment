from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


HYBRID_AGENT_EVENTS = (
    "agent_task_started",
    "agent_plan_created",
    "cloud_context_minimized",
    "cloud_context_redacted",
    "cloud_context_requires_confirmation",
    "permission_confirmation_required",
    "permission_override_required",
    "action_allowed",
    "action_hard_blocked",
    "checkpoint_created",
    "action_executed",
    "observation_recorded",
    "verification_passed",
    "verification_failed",
    "repair_attempted",
    "rollback_attempted",
    "rollback_succeeded",
    "rollback_failed",
    "agent_task_completed",
    "agent_task_stopped_uncertain",
)


@dataclass(frozen=True)
class EvaEvent:
    type: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def event(type_: str, message: str, **payload: Any) -> EvaEvent:
    return EvaEvent(type=type_, message=message, payload=payload)
