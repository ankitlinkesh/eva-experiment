from __future__ import annotations

from .models import SpecialistRole


def list_specialists() -> list[SpecialistRole]:
    return list(_SPECIALISTS)


def get_specialist(specialist_id: str) -> SpecialistRole | None:
    normalized = str(specialist_id or "").strip()
    return next((item for item in _SPECIALISTS if item.id == normalized), None)


def validate_unique_specialist_ids() -> bool:
    ids = [item.id for item in _SPECIALISTS]
    return len(ids) == len(set(ids))


_NO_EXECUTION = (
    "No direct execution. This role only selects safe existing Eva capabilities, "
    "workflow previews, approval gates, and verification surfaces."
)

_SPECIALISTS: tuple[SpecialistRole, ...] = (
    SpecialistRole(
        id="fileagent_workflow_specialist",
        name="FileAgent Workflow Specialist",
        description="Plans FileAgent inspection, draft, approval, sandbox, narrow real-create, verification, and rollback workflows.",
        category="file_workflow",
        primary_capabilities=("eva.fileagent_project_note_workflow", "file.apply_readiness", "file.real_apply_policy"),
        safe_modes=("read_only", "draft_only", "approval_only", "sandbox_only", "phase12l_narrow_real_create"),
        unavailable_actions=("existing-file edits", "source edits", "overwrite", "delete/move/rename/copy"),
        safety_notes=_NO_EXECUTION,
    ),
    SpecialistRole(
        id="codebase_onboarding_specialist",
        name="Codebase Onboarding Specialist",
        description="Helps inspect and explain project structure using read-only FileAgent and planner surfaces.",
        category="project_understanding",
        primary_capabilities=("file.project_inventory", "file.project_explain", "file.understand_text"),
        safe_modes=("read_only", "preview_only"),
        unavailable_actions=("whole-drive scans", "secret reads", "runtime folder dumps"),
        safety_notes=_NO_EXECUTION,
    ),
    SpecialistRole(
        id="technical_writer",
        name="Technical Writer",
        description="Drafts README sections, reports, project notes, and safe text previews without applying them.",
        category="writing",
        primary_capabilities=("file.draft_readme_section", "file.draft_report_outline", "eva.fileagent_project_note_workflow"),
        safe_modes=("draft_only", "preview_only"),
        unavailable_actions=("silent file writes", "overwrite", "source edits"),
        safety_notes=_NO_EXECUTION,
    ),
    SpecialistRole(
        id="reality_checker",
        name="Reality Checker",
        description="Checks whether a claim is actually supported by verifier output, status, or explicit evidence.",
        category="verification",
        primary_capabilities=("eva.phase12_status", "eva.smoke_status", "eva.verify_quick_command"),
        safe_modes=("read_only", "manual_verifier_guidance"),
        unavailable_actions=("claiming tests passed without evidence", "running shell from chat"),
        safety_notes=_NO_EXECUTION,
    ),
    SpecialistRole(
        id="evidence_collector",
        name="Evidence Collector",
        description="Collects local status, verifier command guidance, capability metadata, and FileAgent audit evidence.",
        category="evidence",
        primary_capabilities=("eva.control_center_status", "file.approval_events", "eva.verify_full_command"),
        safe_modes=("read_only", "metadata_only"),
        unavailable_actions=("private data dumps", "absolute path leaks", "raw runtime logs"),
        safety_notes=_NO_EXECUTION,
    ),
    SpecialistRole(
        id="test_results_analyzer",
        name="Test Results Analyzer",
        description="Interprets verifier status and suggests the next safe verification command without running subprocesses.",
        category="verification",
        primary_capabilities=("eva.verify_all", "eva.smoke_status", "eva.phase12_status"),
        safe_modes=("read_only", "manual_verifier_guidance"),
        unavailable_actions=("package installs", "network calls", "automatic verifier execution from chat"),
        safety_notes=_NO_EXECUTION,
    ),
    SpecialistRole(
        id="safety_reviewer",
        name="Safety Reviewer",
        description="Reviews authority decisions, permission posture, and blocked risky execution boundaries.",
        category="safety",
        primary_capabilities=("eva.authority_status", "eva.authority_decision_preview", "file.real_apply_policy"),
        safe_modes=("read_only", "preview_only", "authority_review"),
        unavailable_actions=("MCP execution", "browser control", "desktop control", "terminal execution", "cloud calls"),
        safety_notes=_NO_EXECUTION,
    ),
)
