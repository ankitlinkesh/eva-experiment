from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class StepLimitPolicy:
    default_max_steps: int
    hard_max_steps: int
    runaway_detection: str
    repeated_step_detection: str
    no_progress_detection: str
    stop_behavior: str


@dataclass(frozen=True)
class ActionPreview:
    action_id: str
    action_type: str
    capability_requested: str
    permission_class: str
    risk_level: str
    execution_status: str
    required_approval: str
    blocked_reason: str
    verification_requirement: str
    executed: bool = False
    no_action_executed_statement: str = "No action was executed."


@dataclass(frozen=True)
class MockObservation:
    observation_id: str
    source: str
    summary: str
    trusted: bool
    execution_used: bool = False


@dataclass(frozen=True)
class VerificationNote:
    check_id: str
    status: str
    summary: str


@dataclass(frozen=True)
class AgentLoopState:
    loop_id: str
    request_summary: str
    current_stage: str
    step_count: int
    max_step_limit: int
    selected_capabilities: tuple[str, ...]
    context_packet_summary: str
    threat_scan_summary: str
    planned_preview_steps: tuple[str, ...]
    action_previews: tuple[ActionPreview, ...]
    mock_observations: tuple[MockObservation, ...]
    verification_notes: tuple[VerificationNote, ...]
    blocked_actions: tuple[ActionPreview, ...]
    final_status: str
    stop_reason: str
    no_live_llm_call_statement: str
    no_tool_execution_statement: str
    safety_notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_agent_loop_report

        return format_agent_loop_report(self)


@dataclass(frozen=True)
class AgentLoopStatus:
    status: str
    mode: str
    live_llm_calls_enabled: bool
    provider_sdks_enabled: bool
    tool_execution_enabled: bool
    browser_desktop_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    secret_config_session_reads_enabled: bool
    new_write_paths_enabled: bool
    next_phase: str
