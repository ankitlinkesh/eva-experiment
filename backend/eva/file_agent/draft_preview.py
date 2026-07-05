from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .draft_safety import validate_proposed_file_content
from .path_policy import evaluate_file_path


MAX_EXCERPT_CHARS = 1600
MAX_DIFF_CHARS = 8000


@dataclass(frozen=True)
class DraftPreview:
    path: str
    display_path: str
    operation: str
    allowed: bool
    reason: str
    original_excerpt: str = ""
    proposed_excerpt: str = ""
    diff_preview: str = ""
    estimated_change_size: int = 0
    safety_warnings: list[str] = field(default_factory=list)
    requires_confirmation_for_future_write: bool = True
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __str__(self) -> str:
        return format_draft_preview(self)


@dataclass(frozen=True)
class DraftValidationResult:
    allowed: bool
    reason: str
    warnings: list[str] = field(default_factory=list)
    preview_only: bool = True

    def __str__(self) -> str:
        return format_draft_validation(self)


def create_file_draft_preview(path_text: str, content: str, repo_root: str | Path | None = None) -> DraftPreview:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    safety = validate_proposed_file_content(decision.display_path, content)
    allowed = bool(decision.allowed and not decision.exists and safety.allowed)
    reason = decision.reason
    if decision.exists:
        reason = "Target already exists; create preview would not overwrite it."
        allowed = False
    if not decision.allowed:
        reason = decision.reason
    elif not safety.allowed:
        reason = "Draft target or content failed safety review."
    proposed = _excerpt(safety.redacted_text)
    return DraftPreview(
        path=decision.normalized_path,
        display_path=decision.display_path,
        operation="create_preview",
        allowed=allowed,
        reason=reason,
        proposed_excerpt=proposed,
        diff_preview=_diff("", safety.redacted_text, decision.display_path),
        estimated_change_size=len(str(content or "")),
        safety_warnings=safety.warnings,
    )


def create_text_replacement_preview(path_text: str, old_text: str, new_text: str, repo_root: str | Path | None = None) -> DraftPreview:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    if not decision.allowed:
        return _refused(decision, "replace_preview")
    original, reason = _read_existing_text(decision.normalized_path)
    if original is None:
        return _blocked(decision, "replace_preview", reason)
    safe_new = validate_proposed_file_content(decision.display_path, new_text)
    if old_text not in original:
        return DraftPreview(
            path=decision.normalized_path,
            display_path=decision.display_path,
            operation="replace_preview",
            allowed=False,
            reason="Requested old text was not found. No replacement preview was applied.",
            original_excerpt=_excerpt(original),
            proposed_excerpt="No replacement preview because the old text was not found.",
            safety_warnings=safe_new.warnings,
        )
    proposed = original.replace(old_text, safe_new.redacted_text, 1)
    return DraftPreview(
        path=decision.normalized_path,
        display_path=decision.display_path,
        operation="replace_preview",
        allowed=safe_new.allowed,
        reason="Replacement preview generated. No file was modified." if safe_new.allowed else "Replacement content failed safety review.",
        original_excerpt=_excerpt(original),
        proposed_excerpt=_excerpt(proposed),
        diff_preview=_diff(original, proposed, decision.display_path),
        estimated_change_size=abs(len(proposed) - len(original)),
        safety_warnings=safe_new.warnings,
    )


def create_append_preview(path_text: str, append_text: str, repo_root: str | Path | None = None) -> DraftPreview:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    if not decision.allowed:
        return _refused(decision, "append_preview")
    original, reason = _read_existing_text(decision.normalized_path)
    if original is None:
        return _blocked(decision, "append_preview", reason)
    safety = validate_proposed_file_content(decision.display_path, append_text)
    separator = "" if original.endswith("\n") else "\n"
    proposed = original + separator + safety.redacted_text
    return DraftPreview(
        path=decision.normalized_path,
        display_path=decision.display_path,
        operation="append_preview",
        allowed=safety.allowed,
        reason="Append preview generated. No file was modified." if safety.allowed else "Append content failed safety review.",
        original_excerpt=_excerpt(original[-MAX_EXCERPT_CHARS:]),
        proposed_excerpt=_excerpt(safety.redacted_text),
        diff_preview=_diff(original, proposed, decision.display_path),
        estimated_change_size=len(str(append_text or "")),
        safety_warnings=safety.warnings,
    )


def create_unified_diff_preview(path_text: str, proposed_content: str, repo_root: str | Path | None = None, context_lines: int = 3) -> DraftPreview:
    decision = evaluate_file_path(path_text, repo_root=repo_root)
    if not decision.allowed:
        return _refused(decision, "rewrite_preview")
    original, reason = _read_existing_text(decision.normalized_path)
    if original is None:
        return _blocked(decision, "rewrite_preview", reason)
    safety = validate_proposed_file_content(decision.display_path, proposed_content)
    safe_content = safety.redacted_text
    return DraftPreview(
        path=decision.normalized_path,
        display_path=decision.display_path,
        operation="rewrite_preview",
        allowed=safety.allowed,
        reason="Unified diff preview generated. No file was modified." if safety.allowed else "Proposed content failed safety review.",
        original_excerpt=_excerpt(original),
        proposed_excerpt=_excerpt(safe_content),
        diff_preview=_diff(original, safe_content, decision.display_path, context_lines=context_lines),
        estimated_change_size=abs(len(safe_content) - len(original)),
        safety_warnings=safety.warnings,
    )


def validate_draft_preview(preview: DraftPreview) -> DraftValidationResult:
    warnings = list(preview.safety_warnings)
    if not preview.allowed:
        return DraftValidationResult(False, preview.reason or "Draft preview is not allowed.", warnings)
    if preview.requires_confirmation_for_future_write:
        warnings.append("Any future write would require explicit confirmation, backup, and diff review.")
    return DraftValidationResult(True, "Draft preview is safe to show in chat only.", warnings)


def format_draft_preview(preview: DraftPreview) -> str:
    lines = [
        "FileAgent draft preview",
        "",
        f"Path: {preview.display_path}",
        f"Operation: {preview.operation}",
        f"Status: {'preview generated' if preview.allowed else 'refused or warning'}",
        f"Reason: {preview.reason}",
        "",
        "Safety:",
        "Preview only. No file was created or modified.",
        "Future writes would require confirmation, backup, and diff review.",
    ]
    if preview.safety_warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in preview.safety_warnings)
    if preview.original_excerpt:
        lines.extend(["", "Original excerpt:", _fence(preview.original_excerpt)])
    if preview.proposed_excerpt:
        lines.extend(["", "Proposed excerpt:", _fence(preview.proposed_excerpt)])
    if preview.diff_preview:
        lines.extend(["", "Diff preview:", _fence(preview.diff_preview, "diff")])
    lines.extend(["", f"Estimated change size: {preview.estimated_change_size} characters."])
    return "\n".join(lines)


def format_draft_validation(result: DraftValidationResult) -> str:
    lines = [
        "Draft validation",
        "",
        f"Status: {'allowed for preview' if result.allowed else 'not allowed'}",
        f"Reason: {result.reason}",
    ]
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    lines.extend(["", "Scope: preview only. No file was created or modified."])
    return "\n".join(lines)


def _read_existing_text(path_text: str) -> tuple[str | None, str]:
    path = Path(path_text)
    if not path.exists() or not path.is_file():
        return None, "Target must be an existing safe text file for this preview."
    if path.stat().st_size > 512_000:
        return None, "File is too large for FileAgent draft preview mode."
    try:
        return path.read_text(encoding="utf-8", errors="replace"), "ok"
    except OSError as exc:
        return None, f"Could not read file safely: {type(exc).__name__}."


def _diff(original: str, proposed: str, display_path: str, context_lines: int = 3) -> str:
    lines = list(
        difflib.unified_diff(
            str(original or "").splitlines(),
            str(proposed or "").splitlines(),
            fromfile=display_path,
            tofile=display_path,
            lineterm="",
            n=max(0, min(10, int(context_lines or 3))),
        )
    )
    text = "\n".join(lines)
    if len(text) > MAX_DIFF_CHARS:
        return text[:MAX_DIFF_CHARS] + "\n... diff preview truncated ..."
    return text


def _excerpt(text: str) -> str:
    value = str(text or "")
    if len(value) <= MAX_EXCERPT_CHARS:
        return value
    return value[:MAX_EXCERPT_CHARS] + "\n... preview truncated ..."


def _refused(decision: object, operation: str) -> DraftPreview:
    return DraftPreview(
        path=decision.normalized_path,
        display_path=decision.display_path,
        operation=operation,
        allowed=False,
        reason=decision.reason,
        safety_warnings=["FileAgent path policy refused this target."],
    )


def _blocked(decision: object, operation: str, reason: str) -> DraftPreview:
    return DraftPreview(
        path=decision.normalized_path,
        display_path=decision.display_path,
        operation=operation,
        allowed=False,
        reason=reason,
        safety_warnings=["No file was modified."],
    )


def _fence(text: str, language: str = "text") -> str:
    safe = str(text or "").replace("```", "` ` `")
    return f"```{language}\n{safe}\n```"
