from __future__ import annotations

from dataclasses import replace

from .models import EvaWorkflow
from .registry import get_workflow


def build_fileagent_project_note_workflow(
    request_text: str,
    target_hint: str | None = None,
    content_hint: str | None = None,
) -> EvaWorkflow:
    workflow = get_workflow("fileagent_project_note_create")
    if workflow is None:
        raise RuntimeError("FileAgent project note workflow is not registered")
    target = _safe_hint(target_hint)
    content = _safe_hint(content_hint)
    next_step = _next_step(target, content)
    return replace(
        workflow,
        target_hint=target,
        content_hint=content,
        next_step=next_step,
        metadata={
            "request_summary": _safe_hint(request_text) or "project note request",
            "execution": "not_executed",
            "normal_chat_v2_routing": "disabled",
        },
    )


def format_fileagent_project_note_workflow(workflow_or_request: EvaWorkflow | str, target_hint: str | None = None, content_hint: str | None = None) -> str:
    workflow = workflow_or_request if isinstance(workflow_or_request, EvaWorkflow) else build_fileagent_project_note_workflow(str(workflow_or_request), target_hint, content_hint)
    lines = [
        "FileAgent project note workflow",
        "",
        f"Workflow: {workflow.id}",
        f"Skill: {workflow.skill_id}",
        f"Mode: {workflow.mode}",
        f"Authority: {workflow.authority_category}",
        "Real scope: create-new-text-file only through the Phase 12L gate.",
        "No file was created, edited, deleted, moved, copied, or renamed.",
    ]
    if workflow.target_hint:
        lines.append(f"Target hint: {workflow.target_hint}")
    if workflow.content_hint:
        lines.append(f"Content hint: {workflow.content_hint}")
    lines.extend(["", "Steps:"])
    for index, step in enumerate(workflow.steps, 1):
        flags = []
        if step.requires_confirmation:
            flags.append("confirmation")
        if step.verification_required:
            flags.append("verify")
        if step.rollback_available:
            flags.append("rollback-aware")
        suffix = f" ({', '.join(flags)})" if flags else ""
        lines.append(f"{index}. {step.title}: {step.mode}{suffix}")
        lines.append(f"   {step.description}")
    lines.extend(
        [
            "",
            "Next step:",
            workflow.next_step,
            "",
            "Safety:",
            "The workflow is local and deterministic: no MCP, browser control, desktop control, terminal execution, cloud calls, source edits, overwrites, or broad file writes.",
        ]
    )
    return "\n".join(lines)


def explain_next_workflow_step(workflow: EvaWorkflow) -> str:
    return "\n".join(
        [
            "Next step",
            "",
            workflow.next_step or "Review the workflow plan. No action has been executed.",
            "Real creation, if reached later, still requires an eligible approval id and exact confirmation phrase.",
        ]
    )


def _next_step(target_hint: str | None, content_hint: str | None) -> str:
    if target_hint and content_hint:
        return "Draft the note preview for the hinted target, then create or inspect a FileAgent approval record before any sandbox or real-create gate."
    if target_hint:
        return "Draft safe content for the hinted target, then use FileAgent approval metadata before any apply path."
    return "Choose a safe docs/ or samples/ .md/.txt target and draft the note preview before requesting approval."


def _safe_hint(value: str | None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    if not text:
        return None
    text = text.replace("\\", "/")
    if ":" in text or text.startswith("/") or ".env" in text.lower():
        return "safe relative text target/content hint"
    return text[:180]
