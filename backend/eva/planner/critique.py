from __future__ import annotations

from .models import EvaTaskPlan
from .templates import get_template_for_goal
from .validation import explain_plan_quality, validate_task_plan


def critique_task_plan(plan: EvaTaskPlan) -> list[str]:
    critiques: list[str] = []
    if not plan.steps:
        critiques.append("The plan has no steps.")
    if not any(step.step_type == "verification" or "verify" in step.title.lower() for step in plan.steps):
        critiques.append("Add a verification/checklist step before reporting success.")
    if any(step.permission_status == "confirmation_required" for step in plan.steps):
        critiques.append("Confirmation is correctly separated from drafting, but sending remains unavailable.")
    if any(step.permission_status == "override_required" for step in plan.steps):
        critiques.append("Override-gated risk is identified; a future executor would also need checkpoint/rollback details.")
    if any(step.capability_id is None and step.step_type not in {"planning", "draft_content", "verification", "user_confirmation"} for step in plan.steps):
        critiques.append("Some steps do not map to a registered safe capability yet.")
    if not critiques:
        critiques.append("The plan is clear, preview-only, and permission-aware.")
    return critiques


def suggest_plan_improvements(plan: EvaTaskPlan) -> list[str]:
    suggestions: list[str] = []
    missing = detect_missing_information(plan.user_goal or plan.normalized_goal, plan)
    if missing:
        suggestions.append("Ask for the missing details before a future executor phase.")
    if any(step.step_type == "browser_open" for step in plan.steps):
        suggestions.append("Keep browser work as a public-source research plan until a verified browser executor is enabled.")
    if any(step.step_type == "local_write" for step in plan.steps):
        suggestions.append("Add an explicit save/export confirmation step before any future file write.")
    if any(step.step_type == "user_confirmation" for step in plan.steps):
        suggestions.append("Keep confirmation tied to the exact action, recipient, or target.")
    if not suggestions:
        suggestions.append("Use the plan as a dry-run preview; no task was executed.")
    return suggestions


def detect_missing_information(goal_text: str, plan: EvaTaskPlan) -> list[str]:
    text = _text(goal_text or plan.normalized_goal)
    missing: list[str] = []

    if "hackathon" in text or "submission" in text:
        if not any(term in text for term in ("project ", "repo", "folder", "app name", "project name")):
            missing.append("Which project folder or project name should the submission use?")
        if not any(term in text for term in ("requirements", "rubric", "format", "devpost", "slides", "video")):
            missing.append("What are the submission requirements or expected format?")
        if "deadline" not in text and "due" not in text:
            missing.append("What is the deadline?")

    if "report" in text or "summary" in text or "document" in text:
        if not _has_report_topic(text):
            missing.append("What exact report topic should Eva cover?")
        if not any(term in text for term in ("page", "word", "short", "long", "format", "pdf", "markdown", "docx")):
            missing.append("What length and output format do you want?")
        if not any(term in text for term in ("source", "saved research", "research memory", "web", "notes")):
            missing.append("Which sources should be used?")

    if "send whatsapp" in text or "send email" in text or "message" in text:
        if not any(term in text for term in (" to ", " mom", " dad", " raks", " kutty", " rahul")):
            missing.append("Who is the exact recipient?")
        if not any(term in text for term in (" saying ", " says ", " message ", ":")):
            missing.append("What exact message should be drafted?")

    if "compare" in text and ("motor" in text or "motors" in text):
        if not any(char.isdigit() for char in text) and not any(term in text for term in (" vs ", " versus ", " and ")):
            missing.append("Which motor models or specs should be compared?")
        criteria = ("thrust", "efficiency", "battery", "voltage", "prop", "weight", "kv")
        if not any(term in text for term in criteria):
            missing.append("Which criteria matter: thrust, efficiency, weight, battery voltage, prop size, or KV?")

    if "open chatgpt" in text:
        return []

    return _dedupe(missing)


def format_plan_review(plan: EvaTaskPlan) -> str:
    validation = validate_task_plan(plan)
    template = get_template_for_goal(plan.user_goal or plan.normalized_goal)
    missing = detect_missing_information(plan.user_goal or plan.normalized_goal, plan)
    lines = [
        "Plan review",
        "",
        f"Goal: {plan.user_goal or plan.normalized_goal}",
        f"Template: {template.template_id if template else 'none'}",
        explain_plan_quality(plan, validation),
        "",
        "Critique:",
    ]
    lines.extend(f"- {item}" for item in critique_task_plan(plan))
    lines.extend(["", "Missing information:"])
    if missing:
        lines.extend(f"- {item}" for item in missing)
    else:
        lines.append("- No obvious missing information for this preview.")
    lines.extend(["", "Improvements:"])
    lines.extend(f"- {item}" for item in suggest_plan_improvements(plan))
    lines.extend(["", "Execution: No task was executed. This is a planning-only review."])
    return "\n".join(lines)


def _text(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _has_report_topic(text: str) -> bool:
    generic = {"make report", "create report", "write report", "prepare report", "make a report"}
    if text in generic:
        return False
    return any(term in text for term in ("about ", "on ", "for ", "compare "))


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out

