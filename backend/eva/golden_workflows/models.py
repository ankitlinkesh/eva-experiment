from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class GoldenWorkflowDefinition:
    workflow_id: str
    name: str
    description: str
    risk_level: str
    safe_entrypoint: str
    safety_notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GoldenWorkflowStep:
    step_id: str
    title: str
    status: str
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GoldenWorkflowRun:
    workflow_id: str
    run_id: str
    stage: str
    request_text: str
    target_path: str
    approval_id: str
    created_at: str
    updated_at: str
    steps: list[GoldenWorkflowStep] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GoldenWorkflowResult:
    workflow_id: str
    ok: bool
    stage: str
    summary: str
    target_path: str = ""
    approval_id: str = ""
    next_step: str = ""
    real_create_attempted: bool = False
    rollback_attempted: bool = False
    details: str = ""
    steps: list[GoldenWorkflowStep] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GoldenWorkflowStatus:
    available_workflows: list[GoldenWorkflowDefinition]
    latest_stage: str
    latest_approval_id: str
    pending_approvals: int
    approved_for_future_apply: int
    latest_real_create_status: str
    rollback_available: bool
    next_safe_action: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
