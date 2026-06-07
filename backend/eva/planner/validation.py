from __future__ import annotations

import re
from dataclasses import asdict, field

from ..schemas.modeling import schema_dataclass
from .models import EvaTaskPlan, EvaTaskStep


SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b(?:api[_-]?key|token|password|secret)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
WINDOWS_PATH_RE = re.compile(r"\b[A-Za-z]:\\[^\s]+")


@schema_dataclass
class PlanValidationIssue:
    severity: str
    code: str
    message: str
    step_id: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict


@schema_dataclass
class PlanValidationResult:
    passed: bool
    issues: list[PlanValidationIssue] = field(default_factory=list)
    warnings: list[PlanValidationIssue] = field(default_factory=list)
    quality_score: float = 0.0
    summary: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict


def validate_task_plan(plan: EvaTaskPlan) -> PlanValidationResult:
    issues: list[PlanValidationIssue] = []
    warnings: list[PlanValidationIssue] = []

    if not plan.steps:
        issues.append(_issue("error", "no_steps", "Plan must include at least one step."))

    for step in plan.steps:
        if not step.title.strip() or not step.description.strip():
            issues.append(_issue("error", "missing_step_text", "Each step needs a title and description.", step.step_id))
        if step.risk_level in {"medium", "high"} and not step.permission_status:
            issues.append(_issue("error", "missing_permission", "Risky steps need a permission status.", step.step_id))
        if (step.permission_status == "blocked" or step.availability_status == "blocked") and not step.notes.strip():
            issues.append(_issue("error", "blocked_without_reason", "Blocked steps need notes explaining why.", step.step_id))
        if _is_external_message_step(step) and step.permission_status not in {"confirmation_required", "blocked", "override_required"} and step.step_type != "draft_content":
            issues.append(_issue("error", "message_without_confirmation", "External message steps require confirmation.", step.step_id))
        if _is_destructive_or_system_step(step) and step.permission_status not in {"blocked", "override_required"}:
            issues.append(_issue("error", "destructive_without_override", "Destructive or system steps must be blocked or override-required.", step.step_id))
        if step.capability_id is None and step.availability_status == "available_now" and step.step_type not in {"planning", "verification", "draft_content", "user_confirmation"}:
            warnings.append(_issue("warning", "unknown_available", "Unknown capabilities should not be marked available.", step.step_id))
        if _claims_execution(step):
            issues.append(_issue("error", "execution_claim", "Planner steps must not claim execution happened.", step.step_id))
        for field_name, value in _user_facing_fields(step):
            if _contains_secret(value):
                issues.append(_issue("error", "secret_like_text", f"Secret-looking text found in {field_name}.", step.step_id))
            if WINDOWS_PATH_RE.search(value):
                issues.append(_issue("error", "absolute_path", f"Absolute Windows path found in {field_name}.", step.step_id))

    if plan.can_execute_now:
        issues.append(_issue("error", "planner_marked_executable", "Planner v3 plans must not be marked executable."))
    if not plan.preview_only:
        issues.append(_issue("error", "planner_not_preview_only", "Planner v3 plans must stay preview-only."))
    if _needs_confirmation_checkpoint(plan) and not any(step.permission_status == "confirmation_required" for step in plan.steps):
        issues.append(_issue("error", "missing_confirmation_checkpoint", "External message plan needs a confirmation checkpoint."))
    if _needs_verification(plan) and not any(step.step_type == "verification" or "verify" in step.title.lower() for step in plan.steps):
        warnings.append(_issue("warning", "missing_verification", "Multi-step output plan should include a verification/checklist step."))

    score = compute_plan_quality_score(plan, None, issues, warnings)
    passed = not issues
    if passed and warnings:
        summary = f"Validation passed with {len(warnings)} warning(s)."
    elif passed:
        summary = "Validation passed. Plan is preview-only and permission-aware."
    else:
        summary = f"Validation found {len(issues)} issue(s)."
    return PlanValidationResult(passed=passed, issues=issues, warnings=warnings, quality_score=score, summary=summary)


def compute_plan_quality_score(
    plan: EvaTaskPlan,
    validation_result: PlanValidationResult | None = None,
    issues: list[PlanValidationIssue] | None = None,
    warnings: list[PlanValidationIssue] | None = None,
) -> float:
    if validation_result is not None:
        issues = validation_result.issues
        warnings = validation_result.warnings
    issues = list(issues or [])
    warnings = list(warnings or [])

    score = 0.45
    if plan.steps:
        score += 0.12
    if all(step.title and step.description for step in plan.steps):
        score += 0.10
    if any(step.capability_id for step in plan.steps):
        score += 0.08
    if plan.confirmation_required or plan.override_required or plan.blocked_capabilities:
        score += 0.08
    if any(step.permission_status in {"confirmation_required", "override_required", "blocked"} for step in plan.steps):
        score += 0.06
    if any(step.step_type == "verification" or "verify" in step.title.lower() for step in plan.steps):
        score += 0.08
    if len(plan.steps) >= 4:
        score += 0.05
    if any(step.availability_status == "available_now" for step in plan.steps):
        score += 0.04

    score -= 0.12 * len(issues)
    score -= 0.04 * len(warnings)
    score -= 0.05 * sum(1 for step in plan.steps if step.capability_id is None and step.step_type not in {"planning", "verification", "draft_content", "user_confirmation"})
    return round(max(0.0, min(1.0, score)), 2)


def explain_plan_quality(plan: EvaTaskPlan, validation_result: PlanValidationResult | None = None) -> str:
    result = validation_result or validate_task_plan(plan)
    score = result.quality_score
    if score >= 0.85:
        label = "Strong preview plan"
    elif score >= 0.70:
        label = "Good preview plan"
    elif score >= 0.50:
        label = "Needs more detail"
    else:
        label = "Weak preview plan"
    details: list[str] = []
    if any(step.step_type == "verification" for step in plan.steps):
        details.append("verification included")
    if plan.confirmation_required:
        details.append("confirmation checkpoint included")
    if plan.override_required or plan.blocked_capabilities:
        details.append("blocked or override-gated risk identified")
    if result.warnings:
        details.append(f"{len(result.warnings)} warning(s)")
    if result.issues:
        details.append(f"{len(result.issues)} issue(s)")
    return f"Plan quality: {score:.2f} - {label}. {', '.join(details) if details else result.summary}"


def format_plan_validation(plan_or_result: EvaTaskPlan | PlanValidationResult) -> str:
    result = validate_task_plan(plan_or_result) if isinstance(plan_or_result, EvaTaskPlan) else plan_or_result
    lines = [
        "Plan validation",
        "",
        f"Status: {'passed' if result.passed else 'needs attention'}",
        f"Quality score: {result.quality_score:.2f}",
        f"Summary: {result.summary}",
    ]
    if result.issues:
        lines.extend(["", "Issues:"])
        lines.extend(f"- {issue.message}" for issue in result.issues)
    if result.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning.message}" for warning in result.warnings)
    lines.extend(["", "Scope: validation is read-only and planning-only. No task was executed."])
    return "\n".join(lines)


def _issue(severity: str, code: str, message: str, step_id: str | None = None) -> PlanValidationIssue:
    return PlanValidationIssue(severity=severity, code=code, message=message, step_id=step_id)


def _is_external_message_step(step: EvaTaskStep) -> bool:
    text = " ".join([step.step_type, step.capability_id or "", step.title, step.description]).lower()
    return any(term in text for term in ("whatsapp", "email.send", "external message", "post", "submit form"))


def _is_destructive_or_system_step(step: EvaTaskStep) -> bool:
    text = " ".join([step.step_type, step.capability_id or "", step.title, step.description, step.input_summary]).lower()
    return any(term in text for term in ("file.delete", "delete", "shutdown", "install", "powershell", "run shell", "change settings", "format"))


def _claims_execution(step: EvaTaskStep) -> bool:
    text = " ".join([step.title, step.description, step.expected_output, step.notes]).lower()
    claims = ("executed", "sent successfully", "deleted successfully", "opened browser", "clicked", "installed")
    safe_phrases = ("no execution", "not executed", "does not execute", "without execution", "no task was executed")
    return any(claim in text for claim in claims) and not any(safe in text for safe in safe_phrases)


def _contains_secret(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in SECRET_PATTERNS)


def _user_facing_fields(step: EvaTaskStep) -> list[tuple[str, str]]:
    return [
        ("title", step.title),
        ("description", step.description),
        ("input_summary", step.input_summary),
        ("expected_output", step.expected_output),
        ("notes", step.notes),
    ]


def _needs_confirmation_checkpoint(plan: EvaTaskPlan) -> bool:
    return any(_is_external_message_step(step) for step in plan.steps)


def _needs_verification(plan: EvaTaskPlan) -> bool:
    output_types = {"draft_content", "local_write", "retrieve_memory", "research"}
    return len(plan.steps) > 2 and any(step.step_type in output_types for step in plan.steps)
