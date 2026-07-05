from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CodingClassification:
    task_type: str
    specialist_mode: str
    blocked: bool
    reason: str


@dataclass(frozen=True)
class ProjectContextSummary:
    summary: str
    sources: tuple[str, ...]
    policy: str


@dataclass(frozen=True)
class CodingSpecialistReport:
    coding_report_id: str
    user_request_summary: str
    coding_task_type: str
    selected_specialist_mode: str
    project_context_summary: str
    relevant_safe_context_sources: tuple[str, ...]
    proposed_plan: tuple[str, ...]
    patch_preview_summary: str
    review_checklist: tuple[str, ...]
    test_plan_preview: tuple[str, ...]
    risk_review: tuple[str, ...]
    blocked_actions_with_reasons: tuple[str, ...]
    verification_recommendations: tuple[str, ...]
    handoff_notes: tuple[str, ...]
    final_readiness_status: str
    no_source_edit_statement: str
    no_patch_apply_statement: str
    no_shell_execution_statement: str
    no_test_execution_statement: str
    no_package_install_statement: str
    no_git_operation_statement: str
    no_live_llm_call_statement: str
    no_tool_execution_statement: str
    no_new_write_path_statement: str


@dataclass(frozen=True)
class CodingStatus:
    available: bool
    mode: str
    source_editing_enabled: bool
    patch_application_enabled: bool
    execution_enabled: bool
    readiness: str
    next_phase: str
