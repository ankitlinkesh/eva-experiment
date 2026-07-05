from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskAssessment:
    score: int
    level: str
    factors: tuple[str, ...]


@dataclass(frozen=True)
class EligibilityDecision:
    action_class: str
    gate_decision: str
    permission_class: str
    execution_allowed: bool
    approval_required: bool
    exact_confirmation_required: bool
    reason: str


@dataclass(frozen=True)
class DesktopControlDryRun:
    dry_run_id: str
    requested_action_summary: str
    action_class: str
    target_summary: str
    sensitive_screen_status: str
    required_observation_precondition: str
    risk_score: int
    risk_level: str
    permission_class: str
    gate_decision: str
    approval_requirement: str
    exact_confirmation_requirement: str
    rollback_metadata: str
    audit_metadata: str
    blocked_reason: str
    final_status: str
    execution_performed: bool
    no_click_statement: str
    no_type_statement: str
    no_hotkey_statement: str
    no_clipboard_statement: str
    no_app_control_statement: str
    no_window_control_statement: str
    no_tool_execution_statement: str
    no_new_write_path_statement: str


@dataclass(frozen=True)
class DesktopControlGateStatus:
    available: bool
    mode: str
    real_control_enabled: bool
    observation_mode: str
    readiness: str
    next_phase: str
