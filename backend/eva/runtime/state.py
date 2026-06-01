from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvaRuntimeState:
    user_request: str
    request_id: str = field(default_factory=lambda: uuid4().hex)
    task_id: str = field(default_factory=lambda: uuid4().hex)
    normalized_intent: str = ""
    selected_agent: str | None = None
    task_context: dict[str, Any] = field(default_factory=dict)
    relevant_memory: list[dict[str, Any]] = field(default_factory=list)
    safety_findings: list[dict[str, Any]] = field(default_factory=list)
    permission_decision: dict[str, Any] | None = None
    proposed_actions: list[dict[str, Any]] = field(default_factory=list)
    executed_actions: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    rollback_results: list[dict[str, Any]] = field(default_factory=list)
    dry_run: bool = False
    execution_mode: str = "normal"
    execution_allowed: bool = False
    execution_refused_reason: str | None = None
    execution_bridge_version: str | None = "v2_safe_execution_bridge_v1"
    executed_by: str | None = None
    execution_summary: str | None = None
    skipped_execution_reason: str | None = None
    pending_action: dict[str, Any] | None = None
    plan_summary: str | None = None
    route_score: float | None = None
    route_reason: str | None = None
    provenance: str = "v2_runtime"
    final_response: str = ""
    trace_id: str | None = None
    errors: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def touch(self) -> None:
        self.updated_at = _now()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict
