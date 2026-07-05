from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .approval_ledger import get_file_approval_request
from .draft_safety import detect_secret_like_text
from .path_policy import evaluate_file_path


SAFE_REAL_CREATE_EXTENSIONS = {".md", ".txt"}
SAFE_REAL_CREATE_PARENTS = {"docs", "samples"}
BLOCKED_PREFIXES = (
    ("backend",),
    ("scripts",),
    (".git",),
    (".venv",),
    ("node_modules",),
    ("backend", "eva", "data"),
    ("data",),
    ("logs",),
    ("traces",),
    ("screenshots",),
    ("cache",),
    ("tmp",),
    ("temp",),
)


@dataclass(frozen=True)
class RealApplyEligibility:
    approval_id: str
    display_path: str
    operation: str
    allowed: bool
    reason: str
    required_confirmation_phrase: str
    rollback_available: bool = False
    risk_level: str = "medium"
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return format_real_apply_eligibility(self)


def evaluate_real_apply_eligibility(approval_id: str, repo_root: str | Path | None = None) -> RealApplyEligibility:
    approval = get_file_approval_request(approval_id)
    if approval is None:
        return _eligibility(str(approval_id or "unknown"), "unknown", "unknown", False, "Approval request was not found.", ["Approval request was not found."])
    blockers: list[str] = []
    warnings: list[str] = []
    if approval.status != "approved_for_future_apply":
        blockers.append(f"Approval status must be approved_for_future_apply; current status is {approval.status or 'unknown'}.")
    if approval.operation != "create_preview":
        blockers.append("Phase 12L real apply only supports create-new-file approvals.")
    target = is_safe_real_create_target(approval.display_path, repo_root=repo_root)
    if not target.allowed:
        blockers.extend(target.blockers)
    content = approved_create_content(approval)
    if not content.strip():
        blockers.append("Approved create content is empty or unavailable.")
    if not _is_safe_text_content(content):
        blockers.append("Approved content is not safe plain text.")
    if detect_secret_like_text(content):
        blockers.append("Approved content contains secret-like text.")
    blockers.extend(str(item) for item in getattr(approval, "blockers", []) or [])
    allowed = not blockers
    reason = "Eligible for narrow real create after exact confirmation." if allowed else "Not eligible for narrow real create."
    return RealApplyEligibility(
        approval_id=approval.approval_id,
        display_path=approval.display_path,
        operation=approval.operation,
        allowed=allowed,
        reason=reason,
        required_confirmation_phrase=f"confirm real create {approval.approval_id}",
        rollback_available=allowed,
        risk_level="high",
        blockers=_dedupe(blockers),
        warnings=_dedupe(warnings),
    )


def is_safe_real_create_target(path: str, repo_root: str | Path | None = None) -> RealApplyEligibility:
    display = _display_path(path, repo_root=repo_root)
    blockers: list[str] = []
    normalized_input = str(path or "").strip()
    if not normalized_input:
        blockers.append("Target path is empty.")
    if Path(normalized_input).is_absolute():
        blockers.append("Absolute paths are blocked.")
    if ".." in Path(normalized_input.replace("\\", "/")).parts:
        blockers.append("Path traversal is blocked.")
    decision = evaluate_file_path(normalized_input, repo_root=repo_root)
    if not decision.allowed:
        blockers.append(decision.reason)
    if decision.exists:
        blockers.append("Target already exists; overwrite/edit is blocked.")
    name = Path(display).name
    if name.startswith("."):
        blockers.append("Hidden files are blocked.")
    if any(marker in name.lower() for marker in ("secret", "token", "password", "credential", "cookie", "session")):
        blockers.append("Secret-like filenames are blocked.")
    if not is_allowed_real_create_extension(display):
        blockers.append("Only .md and .txt files can be created by Phase 12L.")
    if not is_allowed_real_create_parent(display, repo_root=repo_root):
        blockers.append("Real create target must be directly under docs/ or samples/.")
    if _blocked_prefix(display):
        blockers.append("Source, runtime, dependency, cache, and generated folders are blocked.")
    allowed = not blockers
    return _eligibility("target-policy", display, "create_preview", allowed, "Target is eligible for narrow real create." if allowed else "Target is blocked.", blockers)


def is_allowed_real_create_extension(path: str) -> bool:
    return Path(str(path or "")).suffix.lower() in SAFE_REAL_CREATE_EXTENSIONS


def is_allowed_real_create_parent(path: str, repo_root: str | Path | None = None) -> bool:
    display = _display_path(path, repo_root=repo_root)
    parts = Path(display.replace("\\", "/")).parts
    if len(parts) != 2:
        return False
    parent = parts[0].lower()
    return parent in SAFE_REAL_CREATE_PARENTS


def is_existing_file_blocked(path: str, repo_root: str | Path | None = None) -> bool:
    return evaluate_file_path(path, repo_root=repo_root).exists


def format_real_apply_policy() -> str:
    return "\n".join(
        [
            "FileAgent narrow real apply policy",
            "",
            "Status: narrowly limited.",
            "Allowed: create-new-text-file only; create a new .md or .txt file directly under docs/ or samples/.",
            "Confirmation: exact phrase `confirm real create <approval_id>` is required.",
            "Verification: created content is read back and compared by hash.",
            "Rollback: only an unchanged Eva-created file can be removed with exact rollback confirmation.",
            "",
            "Blocked:",
            "- existing files cannot be edited or overwritten",
            "- source, config, runtime, database, binary, image, PDF, DOCX, XLSX, lockfile, and hidden files",
            "- delete, move, rename, broad apply, path traversal, absolute paths, and secret-like content",
            "",
            "Scope: Phase 12L only. Broad file writes remain disabled.",
        ]
    )


def format_real_apply_eligibility(result: RealApplyEligibility) -> str:
    lines = [
        "FileAgent real create eligibility",
        "",
        f"Approval ID: {result.approval_id}",
        f"Path: {result.display_path}",
        f"Operation: {result.operation}",
        f"Status: {'eligible' if result.allowed else 'blocked'}",
        f"Risk: {result.risk_level}",
        f"Required confirmation phrase: {result.required_confirmation_phrase}",
        "",
        "Reason:",
        result.reason,
    ]
    if result.blockers:
        lines.append("Blockers:")
        lines.extend(f"- {item}" for item in result.blockers)
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in result.warnings)
    lines.extend(["", "No file was created, edited, overwritten, deleted, moved, or renamed."])
    return "\n".join(lines)


def approved_create_content(approval: object) -> str:
    diff = str(getattr(approval, "diff_preview_redacted", "") or "")
    lines: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _eligibility(approval_id: str, display_path: str, operation: str, allowed: bool, reason: str, blockers: list[str]) -> RealApplyEligibility:
    return RealApplyEligibility(
        approval_id=approval_id,
        display_path=display_path,
        operation=operation,
        allowed=allowed,
        reason=reason,
        required_confirmation_phrase=f"confirm real create {approval_id}",
        risk_level="medium" if allowed else "high",
        blockers=_dedupe(blockers),
    )


def _display_path(path: str, repo_root: str | Path | None = None) -> str:
    root = Path(repo_root or Path.cwd()).resolve()
    text = str(path or "").strip().strip('"').strip("'")
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = root / text
    try:
        resolved = candidate.resolve()
        rel = resolved.relative_to(root)
        return rel.as_posix()
    except Exception:
        return text.replace("\\", "/")


def _blocked_prefix(display_path: str) -> bool:
    parts = tuple(part.lower() for part in Path(display_path.replace("\\", "/")).parts)
    return any(parts[: len(prefix)] == prefix for prefix in BLOCKED_PREFIXES)


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        clean = re.sub(r"\s+", " ", str(item or "")).strip()
        if clean and clean not in out:
            out.append(clean)
    return out


def _is_safe_text_content(text: str) -> bool:
    value = str(text or "")
    if "\x00" in value:
        return False
    for ch in value:
        code = ord(ch)
        if code < 32 and ch not in "\n\r\t":
            return False
    return True
