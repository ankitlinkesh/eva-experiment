from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ActionClassification:
    request_summary: str
    action_class: str
    requested_capability: str
    permission_class: str
    risk_level: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GateEligibility:
    decision_state: str
    approval_requirement: str
    confirmation_requirement: str
    rollback_availability: str
    audit_requirement: str
    blocked_reason: str
    eligible_existing_gate: str
    future_gate_requirement: str
    final_readiness_status: str
    safety_notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GateEvaluation:
    gate_evaluation_id: str
    request_summary: str
    requested_action_class: str
    requested_capability: str
    permission_class: str
    risk_level: str
    decision_state: str
    approval_requirement: str
    confirmation_requirement: str
    rollback_availability: str
    audit_requirement: str
    blocked_reason: str
    eligible_existing_gate: str
    future_gate_requirement: str
    safety_notes: tuple[str, ...]
    final_readiness_status: str
    no_live_llm_call_statement: str
    no_tool_execution_statement: str
    no_new_write_path_statement: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_gate_evaluation

        return format_gate_evaluation(self)


@dataclass(frozen=True)
class ExecutionGateStatus:
    status: str
    mode: str
    live_llm_calls_enabled: bool
    provider_sdks_enabled: bool
    tool_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    arbitrary_file_writes_enabled: bool
    secret_config_session_reads_enabled: bool
    browser_desktop_shell_cloud_mcp_execution_enabled: bool
    new_write_paths_enabled: bool
    existing_real_write_boundary: str
    next_phase: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
