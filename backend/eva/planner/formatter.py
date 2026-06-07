from __future__ import annotations

from .models import EvaTaskPlan
from .status import format_planner_status
from .critique import detect_missing_information, suggest_plan_improvements
from .templates import get_template_for_goal
from .validation import explain_plan_quality, validate_task_plan


def format_task_plan(plan: EvaTaskPlan) -> str:
    template = get_template_for_goal(plan.user_goal or plan.normalized_goal)
    validation = validate_task_plan(plan)
    missing = detect_missing_information(plan.user_goal or plan.normalized_goal, plan)
    lines = [
        "Eva Planner v3 preview",
        "",
        "Goal:",
        plan.user_goal or plan.normalized_goal,
        "",
        "Template:",
        template.template_id if template else "none",
        "",
        "Plan quality:",
        explain_plan_quality(plan, validation).replace("Plan quality: ", "", 1),
        "",
        "Summary:",
        plan.summary,
        "",
        "Plan:",
    ]
    for index, step in enumerate(plan.steps, start=1):
        capability = step.capability_id or "unknown"
        resource = step.resource_id or "unavailable"
        status = _display_status(step.permission_status, step.availability_status)
        lines.extend(
            [
                f"{index}. {step.title}",
                f"   Capability: {capability}",
                f"   Resource: {resource}",
                f"   Status: {status}",
                f"   Why: {step.notes or step.description}",
            ]
        )
    if missing:
        lines.extend(["", "Missing information:"])
        lines.extend(f"- {item}" for item in missing[:6])
    warnings = validation.warnings
    if warnings:
        lines.extend(["", "Validation warnings:"])
        lines.extend(f"- {warning.message}" for warning in warnings[:4])
    improvements = suggest_plan_improvements(plan)
    if improvements:
        lines.extend(["", "Improvements:"])
        lines.extend(f"- {item}" for item in improvements[:4])
    lines.extend(
        [
            "",
            "Safety:",
            plan.safety_summary,
            "",
            "Next:",
            plan.next_recommended_action,
            "",
            "Execution:",
            "No task was executed. This is an explicit planning preview only.",
        ]
    )
    return "\n".join(lines)


def format_plan_summary(plan: EvaTaskPlan) -> str:
    validation = validate_task_plan(plan)
    return "\n".join(
        [
            "Eva Planner v3 summary",
            "",
            f"Goal: {plan.user_goal or plan.normalized_goal}",
            f"Steps: {len(plan.steps)}",
            f"Quality score: {validation.quality_score:.2f}",
            f"Capabilities: {', '.join(plan.required_capabilities) if plan.required_capabilities else 'none'}",
            f"Confirmation required: {'yes' if plan.confirmation_required else 'no'}",
            f"Override required: {'yes' if plan.override_required else 'no'}",
            f"Can execute now: {'yes' if plan.can_execute_now else 'no'}",
            f"Preview only: {'yes' if plan.preview_only else 'no'}",
            "",
            "Safety:",
            plan.safety_summary,
        ]
    )


def _display_status(permission_status: str, availability_status: str) -> str:
    if permission_status == "confirmation_required":
        return "confirmation required"
    if permission_status == "override_required":
        return "override required"
    if permission_status == "blocked" or availability_status == "blocked":
        return "blocked"
    if availability_status == "disabled":
        return "disabled"
    if availability_status == "reference_only":
        return "reference only"
    if availability_status == "missing":
        return "missing"
    if permission_status == "preview_only" or availability_status == "preview_only":
        return "preview only"
    if availability_status == "available_now":
        return "available"
    return "unknown"


__all__ = ["format_task_plan", "format_plan_summary", "format_planner_status"]
