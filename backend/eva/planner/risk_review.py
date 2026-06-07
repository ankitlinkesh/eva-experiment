from __future__ import annotations

from .models import EvaTaskPlan


def identify_blockers(plan: EvaTaskPlan) -> list[str]:
    blockers: list[str] = []
    for step in plan.steps:
        if step.permission_status in {"blocked", "override_required"} or step.availability_status in {"blocked", "disabled", "reference_only", "missing"}:
            label = step.capability_id or step.step_type
            if label not in blockers:
                blockers.append(label)
    return blockers


def identify_confirmation_points(plan: EvaTaskPlan) -> list[str]:
    return [step.step_id for step in plan.steps if step.permission_status == "confirmation_required"]


def summarize_plan_risk(plan: EvaTaskPlan) -> str:
    blockers = identify_blockers(plan)
    confirmations = identify_confirmation_points(plan)
    if blockers:
        return "Some steps are blocked, disabled, missing, or require override. No action should execute from this plan."
    if confirmations:
        return "At least one step needs explicit confirmation before any external-visible action."
    if plan.preview_only:
        return "This is a preview-only plan. It can guide a later explicit command but does not execute anything."
    return "All planned steps are low-risk metadata or read-only steps, but Phase 10A still does not execute them."


def review_plan_risks(plan: EvaTaskPlan) -> EvaTaskPlan:
    blockers = identify_blockers(plan)
    confirmations = identify_confirmation_points(plan)
    plan.blocked_capabilities = blockers
    plan.confirmation_required = bool(confirmations)
    plan.override_required = any(step.permission_status == "override_required" for step in plan.steps)
    plan.preview_only = True
    plan.can_execute_now = False
    plan.safety_summary = summarize_plan_risk(plan)
    if blockers:
        plan.next_recommended_action = "Resolve or remove blocked steps, or run a safer explicit preview command."
    elif confirmations:
        plan.next_recommended_action = "Review the plan and provide explicit confirmation only in a future verified executor phase."
    else:
        plan.next_recommended_action = "Use this plan as a dry-run preview; no task was executed."
    return plan
