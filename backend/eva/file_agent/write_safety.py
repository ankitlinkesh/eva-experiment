from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .draft_preview import DraftPreview
from .path_policy import evaluate_file_path


SAFE_TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".csv",
}

ELIGIBLE_OPERATIONS = {"create_preview", "append_preview", "replace_preview", "rewrite_preview"}


@dataclass(frozen=True)
class WriteEligibilityDecision:
    eligible_for_future_apply: bool
    blocked: bool
    reason: str
    risk_level: str
    requires_confirmation_phrase: bool
    required_confirmation_phrase: str
    requires_backup: bool
    requires_diff_review: bool
    requires_verification: bool
    path_allowed: bool
    content_safe: bool
    operation_allowed_future: bool
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return format_write_eligibility(self)


@dataclass(frozen=True)
class WriteSafetyPlan:
    display_path: str
    operation: str
    eligibility: WriteEligibilityDecision
    confirmation_phrase: str
    backup_steps: list[str] = field(default_factory=list)
    diff_review_steps: list[str] = field(default_factory=list)
    verification_steps: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return format_write_safety_plan(self)


@dataclass(frozen=True)
class RollbackPlan:
    display_path: str
    operation: str
    possible_in_future: bool
    steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return format_rollback_plan(self)


@dataclass(frozen=True)
class VerificationPlan:
    display_path: str
    operation: str
    steps: list[str] = field(default_factory=list)
    confidence_notes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return format_verification_plan(self)


def evaluate_write_eligibility(draft_preview: DraftPreview, repo_root: str | Path | None = None) -> WriteEligibilityDecision:
    decision = evaluate_file_path(draft_preview.display_path, repo_root=repo_root)
    blockers: list[str] = []
    warnings: list[str] = []
    if not decision.allowed:
        blockers.append(decision.reason)
    if not draft_preview.allowed:
        blockers.append(draft_preview.reason)
    if draft_preview.safety_warnings:
        blockers.extend(draft_preview.safety_warnings)
    operation_allowed = draft_preview.operation in ELIGIBLE_OPERATIONS
    if not operation_allowed:
        blockers.append("Only text create, append, replace, and rewrite previews can be considered for future apply.")
    if draft_preview.estimated_change_size > 50_000:
        blockers.append("Change is too large for future apply readiness in this phase.")
    if not _safe_suffix(draft_preview.display_path):
        blockers.append("Target extension is not in the safe text-file allowlist.")
    content_safe = not any("secret-like" in item.lower() or "sensitive" in item.lower() or "runtime" in item.lower() for item in draft_preview.safety_warnings)
    path_allowed = decision.allowed
    requires_backup = draft_preview.operation in {"append_preview", "replace_preview", "rewrite_preview"}
    requires_diff = draft_preview.operation in ELIGIBLE_OPERATIONS
    phrase = _confirmation_phrase(draft_preview.display_path)
    eligible = bool(path_allowed and content_safe and operation_allowed and not blockers)
    risk = "medium"
    if blockers or draft_preview.estimated_change_size > 10_000:
        risk = "high"
    if requires_backup:
        warnings.append("Existing file changes require a backup/checkpoint in a future write phase.")
    warnings.append("Future apply is not enabled in Phase 12D.")
    return WriteEligibilityDecision(
        eligible_for_future_apply=eligible,
        blocked=not eligible,
        reason="Eligible for future confirmed apply planning." if eligible else "Not eligible for future apply until blockers are resolved.",
        risk_level=risk,
        requires_confirmation_phrase=True,
        required_confirmation_phrase=phrase,
        requires_backup=requires_backup,
        requires_diff_review=requires_diff,
        requires_verification=True,
        path_allowed=path_allowed,
        content_safe=content_safe,
        operation_allowed_future=operation_allowed,
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def build_write_safety_plan(draft_preview: DraftPreview, repo_root: str | Path | None = None) -> WriteSafetyPlan:
    eligibility = evaluate_write_eligibility(draft_preview, repo_root=repo_root)
    backup_steps = [
        "Before any future write, capture the current file content or note that the target is new.",
        "Store backup/checkpoint metadata in ignored local runtime storage.",
        "Do not create a backup in Phase 12D.",
    ]
    diff_steps = [
        "Show the unified diff preview to the user.",
        "Require the user to review the exact target path and changed lines.",
    ]
    verification_steps = build_verification_plan(draft_preview, repo_root=repo_root).steps
    notes = [
        "Planning only. No file was created, modified, backed up, or restored.",
        "The confirmation phrase is a future-phase design and is not accepted as execution now.",
    ]
    return WriteSafetyPlan(
        display_path=draft_preview.display_path,
        operation=draft_preview.operation,
        eligibility=eligibility,
        confirmation_phrase=eligibility.required_confirmation_phrase,
        backup_steps=backup_steps,
        diff_review_steps=diff_steps,
        verification_steps=verification_steps,
        notes=notes,
    )


def build_rollback_plan(draft_preview: DraftPreview, repo_root: str | Path | None = None) -> RollbackPlan:
    steps = [
        "Use the future backup/checkpoint captured before applying the change.",
        "Restore the exact previous file content if verification fails.",
        "Read back the target after rollback and compare it with the checkpoint.",
    ]
    warnings = [
        "No backup was created in Phase 12D.",
        "No restoration happened in Phase 12D.",
        "Rollback is only a future plan until write execution exists.",
    ]
    return RollbackPlan(draft_preview.display_path, draft_preview.operation, True, steps, warnings)


def build_verification_plan(draft_preview: DraftPreview, repo_root: str | Path | None = None) -> VerificationPlan:
    steps = [
        "After a future apply, read back the target file safely.",
        "Compare the resulting content or diff against the approved preview.",
        "Confirm the path, operation, and expected changed text match the approved draft.",
    ]
    notes = [
        "Do not mark success only because an apply command returned.",
        "If verification is uncertain, stop and use the rollback plan.",
    ]
    return VerificationPlan(draft_preview.display_path, draft_preview.operation, steps, notes)


def format_write_eligibility(decision: WriteEligibilityDecision) -> str:
    lines = [
        "Write eligibility",
        "",
        f"Status: {'eligible for future confirmed apply' if decision.eligible_for_future_apply else 'not eligible for future apply'}",
        f"Risk: {decision.risk_level}",
        f"Reason: {decision.reason}",
        f"Required confirmation phrase: {decision.required_confirmation_phrase}",
        f"Requires backup: {'yes' if decision.requires_backup else 'no'}",
        f"Requires diff review: {'yes' if decision.requires_diff_review else 'no'}",
        f"Requires verification: {'yes' if decision.requires_verification else 'no'}",
    ]
    if decision.blockers:
        lines.append("Blockers:")
        lines.extend(f"- {item}" for item in decision.blockers)
    if decision.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in decision.warnings)
    lines.extend(["", "Planning only. No file was created, modified, backed up, or restored."])
    return "\n".join(lines)


def format_write_safety_plan(plan: WriteSafetyPlan) -> str:
    lines = [
        "Write safety plan",
        "",
        f"Path: {plan.display_path}",
        f"Operation: {plan.operation}",
        f"Future confirmation phrase: {plan.confirmation_phrase}",
        "",
        "Eligibility:",
        f"- {plan.eligibility.reason}",
        "",
        "Backup/checkpoint plan:",
    ]
    lines.extend(f"- {item}" for item in plan.backup_steps)
    lines.append("Diff review plan:")
    lines.extend(f"- {item}" for item in plan.diff_review_steps)
    lines.append("Verification plan:")
    lines.extend(f"- {item}" for item in plan.verification_steps)
    lines.append("Notes:")
    lines.extend(f"- {item}" for item in plan.notes)
    return "\n".join(lines)


def format_rollback_plan(plan: RollbackPlan) -> str:
    lines = [
        "Rollback plan",
        "",
        f"Path: {plan.display_path}",
        f"Operation: {plan.operation}",
        f"Future rollback possible: {'yes' if plan.possible_in_future else 'no'}",
        "",
        "Steps:",
    ]
    lines.extend(f"- {item}" for item in plan.steps)
    if plan.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in plan.warnings)
    lines.extend(["", "Planning only. No file was created, modified, backed up, or restored."])
    return "\n".join(lines)


def format_verification_plan(plan: VerificationPlan) -> str:
    lines = [
        "Verification plan",
        "",
        f"Path: {plan.display_path}",
        f"Operation: {plan.operation}",
        "",
        "Steps:",
    ]
    lines.extend(f"- {item}" for item in plan.steps)
    if plan.confidence_notes:
        lines.append("Confidence notes:")
        lines.extend(f"- {item}" for item in plan.confidence_notes)
    lines.extend(["", "Planning only. No file was created, modified, backed up, or restored."])
    return "\n".join(lines)


def format_apply_readiness_report(draft_preview: DraftPreview) -> str:
    safety_plan = build_write_safety_plan(draft_preview)
    eligibility = safety_plan.eligibility
    rollback = build_rollback_plan(draft_preview)
    verification = build_verification_plan(draft_preview)
    lines = [
        "Apply readiness",
        "",
        f"Path: {draft_preview.display_path}",
        f"Operation: {draft_preview.operation}",
        f"Status: {'eligible for future confirmed apply' if eligibility.eligible_for_future_apply else 'not eligible for future apply'}",
        f"Risk: {eligibility.risk_level}",
        "",
        "Confirmation:",
        f"- Future phrase: {eligibility.required_confirmation_phrase}",
        "- This phrase is not accepted as execution in Phase 12D.",
        "",
        "Eligibility:",
        f"- {eligibility.reason}",
    ]
    if eligibility.blockers:
        lines.append("Blockers:")
        lines.extend(f"- {item}" for item in eligibility.blockers)
    if eligibility.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in eligibility.warnings)
    lines.extend(["", "Backup/checkpoint plan:"])
    lines.extend(f"- {item}" for item in safety_plan.backup_steps)
    lines.append("Diff review plan:")
    lines.extend(f"- {item}" for item in safety_plan.diff_review_steps)
    lines.append("Verification plan:")
    lines.extend(f"- {item}" for item in verification.steps)
    lines.append("Rollback plan:")
    lines.extend(f"- {item}" for item in rollback.steps)
    lines.extend(["", "Planning only. No file was created, modified, backed up, or restored."])
    return "\n".join(lines)


def format_write_policy(path_text: str | None = None) -> str:
    path = (path_text or "").strip() or "not specified"
    lines = [
        "FileAgent apply policy",
        "",
        f"Target path: {path}",
        "Current state: FileAgent can preview drafts and evaluate apply-readiness, but cannot apply writes yet.",
        "Future apply requires exact confirmation phrase, backup/checkpoint, diff review, verification, and rollback plan.",
        "Blocked: secret paths, runtime/generated data, browser session/profile data, binary files, large changes, delete/move/rename/copy.",
        "",
        "Planning only. No file was created, modified, backed up, or restored.",
    ]
    return "\n".join(lines)


def _confirmation_phrase(display_path: str) -> str:
    return f"confirm apply file draft {display_path}"


def _safe_suffix(display_path: str) -> bool:
    name = Path(display_path).name
    if name in {".gitignore", ".env.example"}:
        return True
    suffix = Path(display_path).suffix.lower()
    return suffix in SAFE_TEXT_SUFFIXES


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output
