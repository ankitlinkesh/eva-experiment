from __future__ import annotations

from .models import BlockedWorkflowStep, WorkflowDependency, WorkflowStep


def build_dependencies(steps: tuple[WorkflowStep, ...], request: str) -> tuple[tuple[WorkflowDependency, ...], tuple[BlockedWorkflowStep, ...]]:
    dependencies: list[WorkflowDependency] = []
    blocked: list[BlockedWorkflowStep] = []
    cycle_requested = "dependency cycle" in str(request or "").lower()
    for index, step in enumerate(steps):
        depends = (steps[index - 1].step_id,) if index else ()
        status = "valid"
        reason = "Sequential preview dependency only."
        if cycle_requested and index == len(steps) - 1 and steps:
            depends = (step.step_id,)
            status = "blocked"
            reason = "Dependency cycle detected and blocked."
            blocked.append(BlockedWorkflowStep(step.step_id, step.step_type, reason))
        dependencies.append(WorkflowDependency(step.step_id, depends, status, reason))
    return tuple(dependencies), tuple(blocked)
