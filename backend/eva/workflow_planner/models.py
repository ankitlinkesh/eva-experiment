from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class WorkflowTemplate:
    template_id: str
    name: str
    category: str
    description: str
    relevance_keywords: tuple[str, ...]
    default_steps: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowStep:
    step_id: str
    title: str
    step_type: str
    capability_id: str
    permission_class: str
    risk_level: str
    preview_summary: str
    executed: bool = False


@dataclass(frozen=True)
class WorkflowDependency:
    step_id: str
    depends_on: tuple[str, ...]
    status: str
    reason: str


@dataclass(frozen=True)
class WorkflowPrecondition:
    precondition_id: str
    description: str
    satisfied: bool
    reason: str


@dataclass(frozen=True)
class WorkflowApprovalRequirement:
    approval_id: str
    requirement: str
    risk_level: str
    execution_unlocked: bool = False


@dataclass(frozen=True)
class WorkflowRollbackPlan:
    status: str
    steps: tuple[str, ...]
    execution_unlocked: bool = False


@dataclass(frozen=True)
class WorkflowVerificationPlan:
    status: str
    checks: tuple[str, ...]
    execution_unlocked: bool = False


@dataclass(frozen=True)
class BlockedWorkflowStep:
    step_id: str
    step_type: str
    reason: str


@dataclass(frozen=True)
class ExcludedWorkflowStep:
    step_type: str
    reason: str


@dataclass(frozen=True)
class WorkflowPlanPreview:
    workflow_id: str
    workflow_name: str
    user_request_summary: str
    selected_template: str
    relevance_score: float
    workflow_category: str
    ordered_steps: tuple[WorkflowStep, ...]
    dependencies: tuple[WorkflowDependency, ...]
    preconditions: tuple[WorkflowPrecondition, ...]
    selected_capabilities: tuple[str, ...]
    permission_classes: tuple[str, ...]
    risk_levels: tuple[str, ...]
    action_previews: tuple[WorkflowStep, ...]
    approval_requirements: tuple[WorkflowApprovalRequirement, ...]
    rollback_plan_preview: WorkflowRollbackPlan
    verification_plan: WorkflowVerificationPlan
    blocked_steps: tuple[BlockedWorkflowStep, ...]
    excluded_steps: tuple[ExcludedWorkflowStep, ...]
    final_readiness_status: str
    no_live_llm_call_statement: str
    no_tool_execution_statement: str
    no_real_write_statement: str
    safety_notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_workflow_report

        return format_workflow_report(self)


@dataclass(frozen=True)
class WorkflowPlannerStatus:
    status: str
    mode: str
    live_llm_calls_enabled: bool
    provider_sdks_enabled: bool
    tool_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    arbitrary_file_writes_enabled: bool
    secret_config_session_reads_enabled: bool
    browser_desktop_execution_enabled: bool
    next_phase: str
