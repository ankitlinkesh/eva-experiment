from __future__ import annotations

from .models import GoldenWorkflowResult, GoldenWorkflowStatus


def format_golden_workflow_status(status: GoldenWorkflowStatus) -> str:
    lines = [
        "Golden Workflows",
        "",
        f"Available workflows: {len(status.available_workflows)}",
    ]
    for workflow in status.available_workflows:
        lines.append(f"- {workflow.workflow_id}: {workflow.name} ({workflow.risk_level})")
    lines.extend(
        [
            "",
            f"Latest stage: {status.latest_stage}",
            f"Latest approval: {status.latest_approval_id or 'none'}",
            f"Pending approvals: {status.pending_approvals}",
            f"Approved for future apply: {status.approved_for_future_apply}",
            f"Latest real-create status: {status.latest_real_create_status}",
            f"Rollback available: {'yes' if status.rollback_available else 'no'}",
            "",
            "Next safe action:",
            status.next_safe_action,
            "",
            "Safety: broad file writes disabled; existing files cannot be edited or overwritten; source/config/runtime files are blocked.",
        ]
    )
    return "\n".join(lines)


def format_golden_workflow_result(result: GoldenWorkflowResult) -> str:
    lines = [
        "Golden Workflow",
        "",
        f"Workflow: {result.workflow_id}",
        f"Stage: {result.stage}",
        f"Status: {'ok' if result.ok else 'stopped'}",
        result.summary,
    ]
    if result.target_path:
        lines.append(f"Target: {result.target_path}")
    if result.approval_id:
        lines.append(f"Approval ID: {result.approval_id}")
    if result.steps:
        lines.extend(["", "Pipeline:"])
        for step in result.steps:
            lines.append(f"- {step.title}: {step.status}; {step.summary}")
    if result.details:
        lines.extend(["", "Details:", result.details])
    if result.next_step:
        lines.extend(["", "Next safe step:", result.next_step])
    lines.extend(["", "No real file was created unless the exact real-create confirmation gate reports success."])
    return "\n".join(lines)


def format_golden_workflow_next_step(result: GoldenWorkflowResult) -> str:
    return result.next_step or "Review the workflow status. No broad write is available."
