from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone

from .models import GoldenWorkflowDefinition, GoldenWorkflowResult, GoldenWorkflowStatus, GoldenWorkflowStep
from .project_note import build_project_note_draft, suggest_safe_target_path


WORKFLOW_ID = "safe_project_note_create"


def list_golden_workflows() -> list[GoldenWorkflowDefinition]:
    return [
        GoldenWorkflowDefinition(
            workflow_id=WORKFLOW_ID,
            name="Safe Project Note Create",
            description="Draft a safe Markdown project note, create an approval, test sandbox apply, then optionally use the narrow real-create gate.",
            risk_level="medium at real-create stage",
            safe_entrypoint="eva ask create a project note about Eva",
            safety_notes="Uses FileAgent approval, sandbox, exact confirmation, verification, and rollback gates. Broad writes remain disabled.",
        )
    ]


def get_golden_workflow_status() -> GoldenWorkflowStatus:
    from ..file_agent.approval_ledger import list_file_approval_requests

    approvals = list_file_approval_requests(limit=100)
    latest = approvals[0] if approvals else None
    pending = len([item for item in approvals if item.status == "pending"])
    approved = len([item for item in approvals if item.status == "approved_for_future_apply"])
    latest_real = "none"
    rollback = False
    if latest:
        latest_real = str(getattr(latest, "real_apply_status", "") or "none")
        rollback = bool(getattr(latest, "real_apply_created_path", "") and getattr(latest, "real_apply_rollback_status", "") != "rolled_back")
    next_action = "Start with `eva ask create a project note about Eva`."
    if pending:
        next_action = "Review the pending approval, then approve it with its exact phrase before sandbox apply."
    elif approved:
        next_action = "Run sandbox apply first, then inspect real-create eligibility if you still want the file."
    elif rollback:
        next_action = "Rollback is available only with `confirm rollback real create <approval_id>`."
    return GoldenWorkflowStatus(
        available_workflows=list_golden_workflows(),
        latest_stage=_stage_from_approval(latest),
        latest_approval_id=getattr(latest, "approval_id", "") if latest else "",
        pending_approvals=pending,
        approved_for_future_apply=approved,
        latest_real_create_status=latest_real,
        rollback_available=rollback,
        next_safe_action=next_action,
    )


def start_safe_project_note_workflow(request_text: str) -> GoldenWorkflowResult:
    from ..file_agent.approval_ledger import create_file_approval_request
    from ..file_agent.draft_preview import create_file_draft_preview

    target = suggest_safe_target_path(request_text)
    draft = build_project_note_draft(request_text)
    preview = create_file_draft_preview(target, draft)
    approval = create_file_approval_request(preview)
    steps = [
        _step("interpret", "Interpret request", "done", "Selected safe_project_note_create."),
        _step("target", "Suggest safe target", "done", target),
        _step("draft", "Generate Markdown draft", "done", "Draft preview generated locally without cloud calls."),
        _step("approval", "Create approval request", approval.status, "Approval metadata recorded; no real file was created."),
    ]
    return GoldenWorkflowResult(
        workflow_id=WORKFLOW_ID,
        ok=approval.status == "pending",
        stage="approval_created" if approval.status == "pending" else "approval_blocked",
        summary="Created a FileAgent approval request for a safe project note." if approval.status == "pending" else "The safe project note approval was blocked by FileAgent policy.",
        target_path=approval.display_path,
        approval_id=approval.approval_id,
        next_step=(
            f"Review the approval, then approve with its exact phrase: `eva file approval approve {approval.approval_id} confirm {approval.required_confirmation_phrase}`. "
            f"After approval, test with `eva file approval sandbox apply {approval.approval_id}`."
        ),
        steps=steps,
    )


def continue_safe_project_note_workflow(request_text: str) -> GoldenWorkflowResult:
    text = str(request_text or "").strip()
    approval_id = _approval_id(text)
    lowered = text.lower()
    if lowered.startswith("confirm real create ") and approval_id:
        return _real_create(approval_id, text)
    if lowered.startswith("confirm rollback real create ") and approval_id:
        return _rollback_real_create(approval_id, text)
    if "rollback" in lowered:
        target = approval_id or "<approval_id>"
        return GoldenWorkflowResult(
            workflow_id=WORKFLOW_ID,
            ok=False,
            stage="rollback_confirmation_required",
            summary="Rollback needs the exact rollback phrase before Eva removes an unchanged Eva-created file.",
            approval_id=approval_id or "",
            next_step=f"Use exactly: `eva ask confirm rollback real create {target}`.",
        )
    if lowered in {"yes", "do it", "go ahead", "apply it", "create it", "continue", "continue golden workflow"} or "continue golden workflow" in lowered:
        return GoldenWorkflowResult(
            workflow_id=WORKFLOW_ID,
            ok=False,
            stage="exact_confirmation_required",
            summary="I will not treat a vague confirmation as approval for real create. An exact phrase is required.",
            approval_id=approval_id or "",
            next_step="Use the exact phrase from the FileAgent approval, run sandbox apply, then use `eva ask confirm real create <approval_id>` only if eligibility says it is safe.",
        )
    return GoldenWorkflowResult(
        workflow_id=WORKFLOW_ID,
        ok=True,
        stage="status",
        summary="Golden workflow status is available.",
        next_step=get_golden_workflow_status().next_safe_action,
        details="Use `eva ask create a project note about Eva` to start, or exact confirmation phrases for gated real create and rollback.",
    )


def _real_create(approval_id: str, phrase: str) -> GoldenWorkflowResult:
    from ..file_agent.real_apply_executor import apply_real_create, build_real_create_request_from_approval, format_real_apply_result

    request = build_real_create_request_from_approval(approval_id, confirmation_phrase=phrase)
    if not request.allowed:
        return GoldenWorkflowResult(
            workflow_id=WORKFLOW_ID,
            ok=False,
            stage="real_create_blocked",
            summary="Real create is blocked until FileAgent eligibility and exact confirmation both pass.",
            target_path=request.display_path,
            approval_id=approval_id,
            real_create_attempted=False,
            next_step=f"Use exactly: `eva ask confirm real create {approval_id}` after approval and sandbox verification.",
            details="; ".join(request.blockers),
        )
    result = apply_real_create(request)
    return GoldenWorkflowResult(
        workflow_id=WORKFLOW_ID,
        ok=result.ok,
        stage="real_create_completed" if result.ok else "real_create_refused",
        summary=result.summary,
        target_path=result.display_path,
        approval_id=approval_id,
        real_create_attempted=True,
        next_step=f"Verify with `eva file real create verify {approval_id}`. Rollback, if unchanged, uses `eva ask confirm rollback real create {approval_id}`.",
        details=format_real_apply_result(result),
    )


def _rollback_real_create(approval_id: str, phrase: str) -> GoldenWorkflowResult:
    from ..file_agent.real_apply_executor import format_real_apply_rollback, rollback_real_create

    result = rollback_real_create(approval_id, confirmation_phrase=phrase)
    return GoldenWorkflowResult(
        workflow_id=WORKFLOW_ID,
        ok=result.success,
        stage="rollback_completed" if result.success else "rollback_refused",
        summary=result.summary,
        target_path=result.display_path,
        approval_id=approval_id,
        rollback_attempted=result.attempted,
        next_step="Check the Control Center status with `eva control center status`.",
        details=format_real_apply_rollback(result),
    )


def _stage_from_approval(approval: object | None) -> str:
    if approval is None:
        return "not_started"
    real_status = str(getattr(approval, "real_apply_status", "") or "")
    rollback_status = str(getattr(approval, "real_apply_rollback_status", "") or "")
    if rollback_status:
        return rollback_status
    if real_status:
        return real_status
    return str(getattr(approval, "status", "") or "unknown")


def _step(step_id: str, title: str, status: str, summary: str) -> GoldenWorkflowStep:
    return GoldenWorkflowStep(step_id=step_id, title=title, status=status, summary=summary)


def _approval_id(text: str) -> str | None:
    match = re.search(r"\b(fap_[a-zA-Z0-9]+)\b", text)
    return match.group(1) if match else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
