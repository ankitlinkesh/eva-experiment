from __future__ import annotations

from .models import WorkflowApprovalRequirement, WorkflowStep


def build_approval_requirements(steps: tuple[WorkflowStep, ...]) -> tuple[WorkflowApprovalRequirement, ...]:
    requirements: list[WorkflowApprovalRequirement] = []
    for step in steps:
        if step.risk_level == "high":
            requirements.append(WorkflowApprovalRequirement(f"apr_{step.step_id}", "Future approval required before any execution gate could exist.", step.risk_level))
        if step.risk_level in {"critical", "forbidden"}:
            requirements.append(WorkflowApprovalRequirement(f"blk_{step.step_id}", "No approval path is available for blocked/refusal preview steps.", step.risk_level))
    return tuple(requirements)
