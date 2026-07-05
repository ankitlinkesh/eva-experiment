from __future__ import annotations

from .models import EvaSkill, EvaWorkflow, SkillStep


def list_skills() -> list[EvaSkill]:
    return list(_SKILLS)


def get_skill(skill_id: str) -> EvaSkill | None:
    normalized = str(skill_id or "").strip()
    return next((item for item in _SKILLS if item.id == normalized), None)


def list_workflows() -> list[EvaWorkflow]:
    return list(_WORKFLOWS)


def get_workflow(workflow_id: str) -> EvaWorkflow | None:
    normalized = str(workflow_id or "").strip()
    return next((item for item in _WORKFLOWS if item.id == normalized), None)


def validate_unique_skill_ids() -> bool:
    ids = [item.id for item in _SKILLS]
    return len(ids) == len(set(ids))


def validate_unique_workflow_ids() -> bool:
    ids = [item.id for item in _WORKFLOWS]
    return len(ids) == len(set(ids))


_SAFE_NOTES = "Local deterministic workflow metadata only; no MCP, browser control, desktop control, terminal execution, cloud call, or broad file write is enabled."

_SKILLS: tuple[EvaSkill, ...] = (
    EvaSkill(
        id="fileagent_create_project_note",
        name="FileAgent Create Project Note",
        description="Guide a safe project-note flow through draft preview, approval, sandbox, narrow real-create eligibility, exact confirmation, verification, and rollback.",
        category="file_workflow",
        specialists=("fileagent_workflow_specialist", "technical_writer", "safety_reviewer", "reality_checker"),
        capabilities=("eva.fileagent_project_note_workflow", "eva.golden_workflow_project_note", "file.real_apply_policy"),
        safe_modes=("workflow_plan_only", "draft_only", "approval_only", "sandbox_only", "phase12l_narrow_real_create"),
        safety_notes=_SAFE_NOTES,
    ),
    EvaSkill(
        id="fileagent_safe_draft",
        name="FileAgent Safe Draft",
        description="Produce chat-only draft previews for README/report/text changes without applying them.",
        category="drafting",
        specialists=("technical_writer", "fileagent_workflow_specialist", "safety_reviewer"),
        capabilities=("file.draft_readme_section", "file.draft_report_outline", "file.diff_preview"),
        safe_modes=("draft_only", "preview_only"),
        safety_notes=_SAFE_NOTES,
    ),
    EvaSkill(
        id="project_inspection_readonly",
        name="Project Inspection Read-only",
        description="Inspect and explain the project through bounded read-only FileAgent surfaces.",
        category="project_understanding",
        specialists=("codebase_onboarding_specialist", "evidence_collector", "safety_reviewer"),
        capabilities=("file.project_inventory", "file.project_explain", "file.understand_text"),
        safe_modes=("read_only", "metadata_only"),
        safety_notes=_SAFE_NOTES,
    ),
    EvaSkill(
        id="verification_before_completion",
        name="Verification Before Completion",
        description="Check evidence, verifier status, and completion claims before saying work is done.",
        category="verification",
        specialists=("reality_checker", "evidence_collector", "test_results_analyzer"),
        capabilities=("eva.smoke_status", "eva.phase12_status", "eva.verify_quick_command", "eva.verify_full_command"),
        safe_modes=("read_only", "manual_verifier_guidance"),
        safety_notes=_SAFE_NOTES,
    ),
    EvaSkill(
        id="safety_status_review",
        name="Safety Status Review",
        description="Review authority, permission, and blocked action posture.",
        category="safety",
        specialists=("safety_reviewer", "reality_checker"),
        capabilities=("eva.authority_status", "file.real_apply_policy", "eva.control_center_status"),
        safe_modes=("read_only", "authority_review"),
        safety_notes=_SAFE_NOTES,
    ),
)


_PROJECT_NOTE_STEPS: tuple[SkillStep, ...] = (
    SkillStep(
        id="understand_request",
        title="Understand project-note target",
        description="Interpret the requested note target and content hints without reading private runtime data.",
        capability_id="eva.natural_router",
        specialist_id="fileagent_workflow_specialist",
        mode="preview_only",
        authority_category="read",
    ),
    SkillStep(
        id="draft_preview",
        title="Draft the note in chat",
        description="Use FileAgent draft preview surfaces to prepare safe markdown/text content.",
        capability_id="file.draft_create_preview",
        specialist_id="technical_writer",
        mode="draft_only",
        authority_category="draft",
    ),
    SkillStep(
        id="approval_metadata",
        title="Create or review approval metadata",
        description="Require a FileAgent approval record before any sandbox or real-create path.",
        capability_id="file.approval_request_create",
        specialist_id="fileagent_workflow_specialist",
        mode="approval_only",
        authority_category="approve",
        requires_confirmation=True,
    ),
    SkillStep(
        id="sandbox_apply",
        title="Sandbox apply and verify",
        description="Apply only inside the ignored FileAgent sandbox and verify sandbox readback.",
        capability_id="file.sandbox_apply_approved",
        specialist_id="reality_checker",
        mode="sandbox_only",
        authority_category="sandbox_apply",
        requires_confirmation=True,
        verification_required=True,
        rollback_available=True,
    ),
    SkillStep(
        id="real_create_gate",
        title="Narrow real create gate",
        description="If eligible, create one brand-new .md/.txt file directly under docs/ or samples/ after exact confirmation.",
        capability_id="file.real_create_new_text_file",
        specialist_id="safety_reviewer",
        mode="phase12l_narrow_real_create",
        authority_category="real_create_safe_text",
        requires_confirmation=True,
        verification_required=True,
        rollback_available=True,
    ),
    SkillStep(
        id="verify_and_report",
        title="Verify and report",
        description="Verify the new file hash or stop honestly if verification is unavailable.",
        capability_id="file.real_verify_new_text_file",
        specialist_id="reality_checker",
        mode="verification",
        authority_category="verify",
        verification_required=True,
        rollback_available=True,
    ),
)

_WORKFLOWS: tuple[EvaWorkflow, ...] = (
    EvaWorkflow(
        id="fileagent_project_note_create",
        name="FileAgent Project Note Create Workflow",
        description="Plan a safe project note through FileAgent draft, approval, sandbox, exact real-create, verification, and rollback gates.",
        skill_id="fileagent_create_project_note",
        specialists=("fileagent_workflow_specialist", "technical_writer", "safety_reviewer", "reality_checker"),
        steps=_PROJECT_NOTE_STEPS,
        mode="workflow_plan_only",
        authority_category="golden_workflow",
        real_execution_scope="phase12l_create_new_text_file_only",
        next_step="Draft the note preview, then create or inspect a FileAgent approval record.",
        safety_notes=_SAFE_NOTES,
    ),
)
