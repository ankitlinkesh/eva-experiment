from __future__ import annotations

from .models import WorkflowPrecondition


def build_preconditions(request: str) -> tuple[WorkflowPrecondition, ...]:
    text = str(request or "").lower()
    missing = "missing approval precondition" in text
    return (
        WorkflowPrecondition("pre_safe_mode", "Workflow planner must remain preview/status/report only.", True, "Local/mock preview mode confirmed."),
        WorkflowPrecondition("pre_no_execution", "No tool, provider, browser, desktop, shell, cloud, MCP, package, or file execution is allowed.", True, "Execution surfaces remain locked."),
        WorkflowPrecondition("pre_future_approval", "High-risk future actions require explicit future approval gates.", not missing, "Missing future approval precondition was reported." if missing else "Approval preview metadata exists."),
    )
