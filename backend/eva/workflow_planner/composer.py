from __future__ import annotations

from .models import BlockedWorkflowStep, ExcludedWorkflowStep, WorkflowStep, WorkflowTemplate
from .risk import classify_workflow_risk, permission_for_risk
from .workflow_policy import ALLOWED_WORKFLOW_STEP_TYPES


_CAPABILITY_FOR_STEP = {
    "status_check_preview": "workflow_planner.status",
    "context_assembly_preview": "context.assemble_preview",
    "threat_scan_preview": "threat.scan_preview",
    "capability_selection_preview": "workflow_planner.preview",
    "agent_loop_preview": "agent_loop.run_preview",
    "fileagent_draft_preview": "file.draft_create_preview",
    "approval_needed_preview": "workflow_planner.approvals",
    "verification_preview": "workflow_planner.preview",
    "rollback_plan_preview": "workflow_planner.rollback",
    "clarification_preview": "workflow_planner.preview",
    "refusal_preview": "workflow_planner.preview",
    "final_report_preview": "workflow_planner.preview",
}


def compose_workflow_steps(request: str, template: WorkflowTemplate) -> tuple[tuple[WorkflowStep, ...], tuple[BlockedWorkflowStep, ...], tuple[ExcludedWorkflowStep, ...]]:
    risk = classify_workflow_risk(request, template.category)
    permission = permission_for_risk(risk)
    blocked: list[BlockedWorkflowStep] = []
    excluded: list[ExcludedWorkflowStep] = []
    steps: list[WorkflowStep] = []
    for index, step_type in enumerate(template.default_steps, start=1):
        if step_type not in ALLOWED_WORKFLOW_STEP_TYPES:
            excluded.append(ExcludedWorkflowStep(step_type, "Step type is not in the allowed preview list."))
            continue
        if template.category == "refusal_or_blocked" and step_type != "final_report_preview":
            blocked.append(BlockedWorkflowStep(f"wfs_{index:02d}", step_type, _blocked_reason(request)))
        steps.append(
            WorkflowStep(
                step_id=f"wfs_{index:02d}",
                title=step_type.replace("_", " ").title(),
                step_type=step_type,
                capability_id=_CAPABILITY_FOR_STEP.get(step_type, "workflow_planner.preview"),
                permission_class=permission,
                risk_level=risk,
                preview_summary="Preview metadata only; no tool, browser, desktop, shell, cloud, MCP, provider, or file execution.",
            )
        )
    return tuple(steps), tuple(blocked), tuple(excluded)


def _blocked_reason(request: str) -> str:
    text = str(request or "").lower()
    if any(term in text for term in (".env", "secret", "token", "cookie", "password", "session")):
        return "Secrets/config/session data are blocked."
    if "arbitrary file" in text or "write arbitrary" in text:
        return "Arbitrary file reads/writes are blocked."
    if any(term in text for term in ("shell", "browser", "desktop", "cloud", "mcp", "package", "execute", "tool")):
        return "Browser/desktop/shell/cloud/MCP execution remains locked; tools are not executed."
    if "super_execute" in text:
        return "Unknown or hallucinated workflow capability was rejected."
    return "Unsupported workflow became a blocked/refusal preview."
