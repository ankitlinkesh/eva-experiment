from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SystemMapEntry:
    feature_name: str
    phase: str
    state: str
    allowed_mode: str
    summary: str


@dataclass(frozen=True)
class PhaseHealthEntry:
    phase: str
    feature_name: str
    health: str
    source: str
    notes: str


@dataclass(frozen=True)
class CapabilityMatrixEntry:
    feature_name: str
    phase: str
    current_state: str
    allowed_mode: str
    execution_allowed: bool
    write_allowed: bool
    approval_behavior: str
    confirmation_behavior: str
    safety_notes: str
    next_safe_action: str


@dataclass(frozen=True)
class AIOSDashboard:
    dashboard_id: str
    current_phase: str
    overall_readiness: str
    master_verification_summary: str
    phase_health_summary: str
    system_map_summary: str
    capability_matrix_summary: str
    preview_only_features: tuple[str, ...]
    existing_narrow_real_gate_summary: str
    locked_future_gates: tuple[str, ...]
    blocked_action_classes: tuple[str, ...]
    safety_boundary_summary: str
    recent_limitation_summary: str
    next_recommended_safe_step: str
    no_live_llm_call_statement: str
    no_tool_execution_statement: str
    no_new_write_path_statement: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_dashboard

        return format_dashboard(self)


@dataclass(frozen=True)
class AIOSStatus:
    status: str
    mode: str
    current_phase: str
    overall_readiness: str
    live_llm_calls_enabled: bool
    provider_sdks_enabled: bool
    tool_execution_enabled: bool
    web_server_enabled: bool
    browser_launch_enabled: bool
    desktop_ui_enabled: bool
    background_daemon_enabled: bool
    arbitrary_file_reads_enabled: bool
    arbitrary_file_writes_enabled: bool
    next_phase: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
