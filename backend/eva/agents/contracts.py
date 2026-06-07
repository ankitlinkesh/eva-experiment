from __future__ import annotations

from dataclasses import asdict, field
from typing import Any

from ..schemas.modeling import schema_dataclass


@schema_dataclass
class EvaAgentRequest:
    request_id: str
    user_goal: str
    task_step_id: str | None
    capability_id: str | None
    resource_id: str | None
    input_summary: str
    context: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    execution_allowed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class EvaAgentResponse:
    agent_name: str
    request_id: str
    task_step_id: str | None
    action: str
    status: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    required_permission: str | None = None
    risk_level: str = "low"
    capability_id: str | None = None
    resource_id: str | None = None
    observations: list[str] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    next_action: str = "No task was executed."

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict


def request_from_any(value: Any) -> EvaAgentRequest:
    if isinstance(value, EvaAgentRequest):
        return value
    user_goal = str(getattr(value, "normalized_intent", "") or getattr(value, "user_request", "") or value or "")
    return EvaAgentRequest(
        request_id="req_preview",
        user_goal=user_goal,
        task_step_id=getattr(value, "step_id", None),
        capability_id=getattr(value, "capability_id", None),
        resource_id=getattr(value, "resource_id", None),
        input_summary=str(getattr(value, "input_summary", "") or user_goal),
        context={},
        dry_run=True,
        execution_allowed=False,
    )

