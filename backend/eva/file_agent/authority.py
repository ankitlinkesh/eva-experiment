from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .draft_preview import DraftPreview
from .write_safety import evaluate_write_eligibility
from ..authority.decision import (
    allow_approval_decision,
    allow_draft_decision,
    allow_readonly_decision,
    allow_sandbox_decision,
    block_real_execution_decision,
)
from ..authority.models import AuthorityDecision


@dataclass(frozen=True)
class FileAuthorityDecision:
    authority_level: str
    safe_preview_allowed: bool
    approval_request_allowed: bool
    actual_apply_allowed: bool
    reason: str
    required_future_steps: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return format_file_authority_decision(self)


@dataclass(frozen=True)
class FileSandboxAuthorityDecision:
    authority_level: str
    sandbox_apply_allowed: bool
    real_apply_allowed: bool
    reason: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_file_authority_for_approval(
    draft_preview: DraftPreview,
    user_context: dict[str, Any] | None = None,
) -> FileAuthorityDecision:
    eligibility = evaluate_write_eligibility(draft_preview)
    blockers = list(eligibility.blockers)
    warnings = list(eligibility.warnings)
    if not _safe_text_operation(draft_preview):
        blockers.append("Only safe text-file draft previews can create approval records.")
    if not _safe_text_suffix(draft_preview.display_path):
        blockers.append("Target extension is not eligible for approval recording.")
    allowed = bool(eligibility.eligible_for_future_apply and not blockers)
    return FileAuthorityDecision(
        authority_level="approval_recording_only",
        safe_preview_allowed=True,
        approval_request_allowed=allowed,
        actual_apply_allowed=False,
        reason="Approval metadata can be recorded for a future gated apply." if allowed else "Approval recording is blocked until FileAgent safety checks pass.",
        required_future_steps=[
            "Re-check path policy.",
            "Re-check content safety.",
            "Create backup/checkpoint.",
            "Apply the approved diff in a future executor phase.",
            "Verify the result by reading back the target.",
            "Keep rollback available if verification fails.",
        ],
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings + ["Actual file apply is disabled in Phase 12E."]),
    )


def evaluate_file_authority_for_sandbox_apply(approval_request: Any | None) -> FileSandboxAuthorityDecision:
    if approval_request is None:
        return FileSandboxAuthorityDecision(
            authority_level="sandbox_apply_only",
            sandbox_apply_allowed=False,
            real_apply_allowed=False,
            reason="Approval request was not found.",
            blockers=["Approval request was not found."],
        )
    blockers: list[str] = []
    warnings: list[str] = ["Real file apply is disabled; only sandbox apply can be tested."]
    status = str(getattr(approval_request, "status", "") or "")
    operation = str(getattr(approval_request, "operation", "") or "")
    display_path = str(getattr(approval_request, "display_path", "") or "")
    if status != "approved_for_future_apply":
        blockers.append(f"Approval status must be approved_for_future_apply; current status is {status or 'unknown'}.")
    if operation not in {"create_preview", "append_preview", "replace_preview", "rewrite_preview"}:
        blockers.append("Only safe text create, append, replace, and rewrite approvals can run in the sandbox harness.")
    if not _safe_text_suffix(display_path):
        blockers.append("Target extension is not eligible for sandbox apply.")
    if not str(getattr(approval_request, "diff_preview_redacted", "") or "").strip():
        blockers.append("No safe diff preview is available for sandbox apply.")
    for item in list(getattr(approval_request, "blockers", []) or []):
        blockers.append(str(item))
    allowed = not blockers
    return FileSandboxAuthorityDecision(
        authority_level="sandbox_apply_only",
        sandbox_apply_allowed=allowed,
        real_apply_allowed=False,
        reason="Approved metadata can run through the sandbox apply harness only." if allowed else "Sandbox apply is blocked until approval safety checks pass.",
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def format_file_authority_decision(decision: FileAuthorityDecision) -> str:
    lines = [
        "File authority decision",
        "",
        f"Authority level: {decision.authority_level}",
        f"Safe preview allowed: {'yes' if decision.safe_preview_allowed else 'no'}",
        f"Approval request allowed: {'yes' if decision.approval_request_allowed else 'no'}",
        f"Actual apply allowed: {'yes' if decision.actual_apply_allowed else 'no'}",
        f"Reason: {decision.reason}",
    ]
    if decision.required_future_steps:
        lines.append("Future required steps:")
        lines.extend(f"- {item}" for item in decision.required_future_steps)
    if decision.blockers:
        lines.append("Blockers:")
        lines.extend(f"- {item}" for item in decision.blockers)
    if decision.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in decision.warnings)
    lines.extend(["", "No file was created, modified, backed up, restored, or applied."])
    return "\n".join(lines)


def file_authority_to_global_decision(
    decision: FileAuthorityDecision | FileSandboxAuthorityDecision,
    *,
    action_type: str,
    capability_id: str | None = None,
    approval_id: str | None = None,
) -> AuthorityDecision:
    if isinstance(decision, FileSandboxAuthorityDecision):
        if decision.sandbox_apply_allowed:
            return allow_sandbox_decision(
                action_type=action_type,
                action_category="sandbox_apply",
                capability_id=capability_id or "file.sandbox_apply_approved",
                agent_name="FileAgent",
                approval_id=approval_id,
                reason=decision.reason,
                requires_approval=True,
                public_mode_allowed=False,
            )
        return block_real_execution_decision(
            action_type=action_type,
            action_category="sandbox_apply",
            capability_id=capability_id or "file.sandbox_apply_approved",
            agent_name="FileAgent",
            approval_id=approval_id,
            reason=decision.reason,
            blocked_reason="; ".join(decision.blockers) or "Sandbox apply is blocked.",
            public_mode_allowed=False,
        )
    if decision.approval_request_allowed:
        return allow_approval_decision(
            action_type=action_type,
            action_category="approve",
            capability_id=capability_id or "file.approval_request_create",
            agent_name="FileAgent",
            reason=decision.reason,
            public_mode_allowed=False,
        )
    if decision.safe_preview_allowed:
        return allow_draft_decision(
            action_type=action_type,
            action_category="draft",
            capability_id=capability_id or "file.draft_create_preview",
            agent_name="FileAgent",
            reason=decision.reason,
        )
    return allow_readonly_decision(
        action_type=action_type,
        action_category="read",
        capability_id=capability_id or "file.inspect_path",
        agent_name="FileAgent",
        reason=decision.reason,
    )


def _safe_text_operation(draft_preview: DraftPreview) -> bool:
    return draft_preview.operation in {"create_preview", "append_preview", "replace_preview", "rewrite_preview"}


def _safe_text_suffix(display_path: str) -> bool:
    name = Path(display_path).name
    if name in {".gitignore", ".env.example"}:
        return True
    return Path(display_path).suffix.lower() in {
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


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output
