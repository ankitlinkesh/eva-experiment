from __future__ import annotations

from dataclasses import asdict, field
from datetime import UTC, datetime

from ..schemas.modeling import schema_dataclass


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


@schema_dataclass
class EvaTaskStep:
    step_id: str
    title: str
    description: str
    step_type: str
    capability_id: str | None
    resource_id: str | None
    agent: str | None
    input_summary: str
    expected_output: str
    risk_level: str
    permission_status: str
    availability_status: str
    depends_on: list[str] = field(default_factory=list)
    status: str = "planned"
    notes: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class EvaTaskPlan:
    plan_id: str
    user_goal: str
    normalized_goal: str
    summary: str
    steps: list[EvaTaskStep]
    required_capabilities: list[str]
    blocked_capabilities: list[str]
    confirmation_required: bool
    override_required: bool
    can_execute_now: bool
    preview_only: bool
    safety_summary: str
    next_recommended_action: str
    created_at: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class EvaPlannerStatus:
    planner_version: str
    planning_only: bool
    execution_enabled: bool
    supported_goal_types: list[str]
    safety_summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict
