from __future__ import annotations

from dataclasses import asdict, dataclass, field


WORK_SESSION_EVENT_TYPES = {
    "request_received",
    "intent_routed",
    "specialist_selected",
    "skill_selected",
    "workflow_selected",
    "planner_steps_created",
    "authority_decision",
    "approval_needed",
    "approval_selected",
    "sandbox_apply_seen",
    "real_create_seen",
    "verification_seen",
    "rollback_available",
    "blocked_action",
    "final_report",
}


@dataclass(frozen=True)
class WorkSessionEvent:
    event_id: str
    session_id: str
    event_type: str
    summary: str
    metadata: dict[str, object] = field(default_factory=dict)
    created_at: str = ""
    sequence: int = 0

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WorkSession:
    session_id: str
    user_request: str
    source: str = "eva ask"
    interpreted_intent: str = ""
    status: str = "active"
    selected_specialists: tuple[str, ...] = ()
    selected_skills: tuple[str, ...] = ()
    selected_workflow: str = ""
    planner_steps: tuple[str, ...] = ()
    authority_decision: str = ""
    approval_id: str = ""
    sandbox_apply_status: str = ""
    real_create_status: str = ""
    verification_status: str = ""
    rollback_status: str = ""
    final_summary: str = ""
    next_safe_step: str = ""
    created_at: str = ""
    updated_at: str = ""
    closed_at: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
