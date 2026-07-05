from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .approval_ledger import get_file_approval_request, record_file_approval_event, update_file_approval_real_apply
from .real_apply_policy import approved_create_content, evaluate_real_apply_eligibility, format_real_apply_policy, is_safe_real_create_target
from ..authority.decision import allow_real_execution_decision, block_real_execution_decision
from ..authority.formatter import format_authority_decision
from ..authority.models import AuthorityDecision


@dataclass(frozen=True)
class RealApplyRequest:
    approval_id: str
    display_path: str
    operation: str
    content: str
    content_hash: str
    allowed: bool
    reason: str
    required_confirmation_phrase: str
    confirmation_phrase: str
    authority: AuthorityDecision
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RealApplyResult:
    approval_id: str
    ok: bool
    display_path: str
    content_hash: str
    created: bool
    verified: bool
    summary: str
    error: str | None = None
    authority: AuthorityDecision | None = None


@dataclass(frozen=True)
class RealApplyVerificationResult:
    approval_id: str
    verified: bool
    confidence: float
    display_path: str
    evidence: str
    failure_reason: str | None = None


@dataclass(frozen=True)
class RealApplyRollbackResult:
    approval_id: str
    attempted: bool
    success: bool
    display_path: str
    summary: str
    error: str | None = None


def build_real_create_request_from_approval(
    approval_id: str,
    *,
    confirmation_phrase: str = "",
    repo_root: str | Path | None = None,
) -> RealApplyRequest:
    approval = get_file_approval_request(approval_id)
    eligibility = evaluate_real_apply_eligibility(approval_id, repo_root=repo_root)
    required = eligibility.required_confirmation_phrase
    phrase_ok = str(confirmation_phrase or "").strip() == required
    content = approved_create_content(approval) if approval else ""
    blockers = list(eligibility.blockers)
    if not phrase_ok:
        blockers.append(f"Exact confirmation phrase required: {required}")
    allowed = eligibility.allowed and phrase_ok
    authority = _authority_for_request(approval_id, eligibility.display_path, allowed, "; ".join(blockers) or eligibility.reason)
    return RealApplyRequest(
        approval_id=approval_id,
        display_path=eligibility.display_path,
        operation=eligibility.operation,
        content=content,
        content_hash=_hash(content),
        allowed=allowed,
        reason="Ready for narrow real create." if allowed else "Real create is blocked.",
        required_confirmation_phrase=required,
        confirmation_phrase=str(confirmation_phrase or "").strip(),
        authority=authority,
        blockers=_dedupe(blockers),
    )


def evaluate_real_create_request(request: RealApplyRequest) -> AuthorityDecision:
    return request.authority


def create_real_create_checkpoint(request: RealApplyRequest) -> str:
    record_file_approval_event(request.approval_id, "real_create_checkpoint_created", "Checkpoint recorded: target must not exist before exclusive create.")
    return "target_absent_checkpoint"


def apply_real_create(request: RealApplyRequest, repo_root: str | Path | None = None) -> RealApplyResult:
    record_file_approval_event(request.approval_id, "real_apply_eligibility_checked", "Narrow real apply eligibility checked.")
    record_file_approval_event(request.approval_id, "real_create_requested", "Narrow real create requested.")
    record_file_approval_event(request.approval_id, "real_create_eligibility_checked", "Real-create policy and approval status checked.")
    if not request.allowed:
        record_file_approval_event(request.approval_id, "real_apply_refused", request.reason)
        record_file_approval_event(request.approval_id, "real_create_refused", request.reason)
        return RealApplyResult(request.approval_id, False, request.display_path, request.content_hash, False, False, "Real create refused.", "; ".join(request.blockers), request.authority)
    record_file_approval_event(request.approval_id, "real_apply_confirmation_required", "Exact real-create confirmation phrase is required and was provided.")
    record_file_approval_event(request.approval_id, "real_create_confirmed", "Exact real-create confirmation phrase accepted.")
    root = Path(repo_root or Path.cwd()).resolve()
    target = (root / request.display_path).resolve()
    target_policy = is_safe_real_create_target(request.display_path, repo_root=root)
    if not target_policy.allowed:
        record_file_approval_event(request.approval_id, "real_apply_refused", target_policy.reason)
        record_file_approval_event(request.approval_id, "real_create_refused", target_policy.reason)
        return RealApplyResult(request.approval_id, False, request.display_path, request.content_hash, False, False, "Real create refused.", "; ".join(target_policy.blockers), request.authority)
    create_real_create_checkpoint(request)
    record_file_approval_event(request.approval_id, "real_apply_create_started", "Narrow real create-new-text-file operation started.")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", encoding="utf-8", newline="") as handle:
            handle.write(request.content)
    except FileExistsError:
        record_file_approval_event(request.approval_id, "real_apply_refused", "Target already exists; overwrite refused.")
        record_file_approval_event(request.approval_id, "real_create_refused", "Target already exists; overwrite refused.")
        return RealApplyResult(request.approval_id, False, request.display_path, request.content_hash, False, False, "Real create refused.", "target_exists", request.authority)
    except OSError as exc:
        record_file_approval_event(request.approval_id, "real_apply_refused", f"Create failed: {type(exc).__name__}.")
        record_file_approval_event(request.approval_id, "real_create_refused", f"Create failed: {type(exc).__name__}.")
        return RealApplyResult(request.approval_id, False, request.display_path, request.content_hash, False, False, "Real create refused.", type(exc).__name__, request.authority)
    verification = _verify_target(target, request.content_hash)
    update_file_approval_real_apply(
        request.approval_id,
        status="consumed_by_real_create",
        event_type="real_apply_create_completed",
        message="Narrow real create-new-text-file operation completed.",
        real_apply_status="created",
        real_apply_mode="real_create_new_text_file",
        real_apply_created_path=request.display_path,
        real_apply_created_hash=request.content_hash,
        real_apply_verified_at=_now() if verification else "",
    )
    record_file_approval_event(request.approval_id, "real_create_completed", "Real create completed for a new safe text file.")
    record_file_approval_event(request.approval_id, "real_apply_verify_passed" if verification else "real_apply_verify_failed", "Created content hash matched approved content." if verification else "Created content hash did not match approved content.")
    record_file_approval_event(request.approval_id, "real_create_verify_passed" if verification else "real_create_verify_failed", "Created content hash matched approved content." if verification else "Created content hash did not match approved content.")
    return RealApplyResult(
        request.approval_id,
        True,
        request.display_path,
        request.content_hash,
        True,
        verification,
        "Real create completed. Narrow real create-new-text-file operation completed. No existing file was edited or overwritten.",
        None,
        request.authority,
    )


def verify_real_create(approval_id: str, repo_root: str | Path | None = None) -> RealApplyVerificationResult:
    approval = get_file_approval_request(approval_id)
    if approval is None:
        return RealApplyVerificationResult(approval_id, False, 0.0, "unknown", "Approval was not found.", "approval_missing")
    path = str(getattr(approval, "real_apply_created_path", "") or "")
    expected_hash = str(getattr(approval, "real_apply_created_hash", "") or "")
    if not path or not expected_hash:
        return RealApplyVerificationResult(approval_id, False, 0.1, path or approval.display_path, "No real-create record exists.", "missing_real_create_record")
    target = (Path(repo_root or Path.cwd()).resolve() / path).resolve()
    if not target.exists() or not target.is_file():
        return RealApplyVerificationResult(approval_id, False, 0.2, path, "Created file is missing.", "missing_file")
    verified = _verify_target(target, expected_hash)
    record_file_approval_event(approval_id, "real_apply_verify_passed" if verified else "real_apply_verify_failed", "Real-create verification checked current file hash.")
    record_file_approval_event(approval_id, "real_create_verify_passed" if verified else "real_create_verify_failed", "Real-create verification checked current file hash.")
    return RealApplyVerificationResult(
        approval_id,
        verified,
        1.0 if verified else 0.3,
        path,
        "Created file content matches approved hash." if verified else "Created file content no longer matches approved hash.",
        None if verified else "hash_mismatch",
    )


def rollback_real_create(
    result_or_approval_id: RealApplyResult | str,
    *,
    confirmation_phrase: str = "",
    repo_root: str | Path | None = None,
) -> RealApplyRollbackResult:
    approval_id = result_or_approval_id.approval_id if isinstance(result_or_approval_id, RealApplyResult) else str(result_or_approval_id or "")
    required = f"confirm rollback real create {approval_id}"
    record_file_approval_event(approval_id, "real_apply_rollback_requested", "Rollback requested for narrow real create.")
    record_file_approval_event(approval_id, "real_create_rollback_requested", "Rollback requested for narrow real create.")
    if str(confirmation_phrase or "").strip() != required:
        record_file_approval_event(approval_id, "real_apply_rollback_refused", "Exact rollback confirmation phrase was not provided.")
        record_file_approval_event(approval_id, "real_create_rollback_refused", "Exact rollback confirmation phrase was not provided.")
        return RealApplyRollbackResult(approval_id, False, False, "unknown", f"Rollback refused. Exact phrase required: {required}", "confirmation_required")
    approval = get_file_approval_request(approval_id)
    if approval is None:
        return RealApplyRollbackResult(approval_id, True, False, "unknown", "Rollback refused because approval record was not found.", "approval_missing")
    path = str(getattr(approval, "real_apply_created_path", "") or "")
    expected_hash = str(getattr(approval, "real_apply_created_hash", "") or "")
    if not path or not expected_hash:
        record_file_approval_event(approval_id, "real_apply_rollback_refused", "No Eva-created real-create record exists.")
        record_file_approval_event(approval_id, "real_create_rollback_refused", "No Eva-created real-create record exists.")
        return RealApplyRollbackResult(approval_id, True, False, approval.display_path, "Rollback refused because no Eva-created file record exists.", "missing_real_create_record")
    target = (Path(repo_root or Path.cwd()).resolve() / path).resolve()
    target_policy = is_safe_real_create_target(path, repo_root=repo_root)
    if target_policy.allowed:
        # The target currently exists, so the normal create policy will be blocked by existence. Check the static folder/suffix pieces via the original path.
        pass
    if not target.exists() or not target.is_file():
        record_file_approval_event(approval_id, "real_apply_rollback_refused", "Created file was already missing.")
        record_file_approval_event(approval_id, "real_create_rollback_refused", "Created file was already missing.")
        return RealApplyRollbackResult(approval_id, True, False, path, "Rollback refused because the created file is missing.", "missing_file")
    if not _verify_target(target, expected_hash):
        record_file_approval_event(approval_id, "real_apply_rollback_refused", "Created file changed after apply; rollback refused.")
        record_file_approval_event(approval_id, "real_create_rollback_refused", "Created file changed after apply; rollback refused.")
        return RealApplyRollbackResult(approval_id, True, False, path, "Rollback refused because the file changed after Eva created it.", "hash_mismatch")
    try:
        target.unlink()
    except OSError as exc:
        record_file_approval_event(approval_id, "real_apply_rollback_refused", f"Rollback delete failed: {type(exc).__name__}.")
        record_file_approval_event(approval_id, "real_create_rollback_refused", f"Rollback delete failed: {type(exc).__name__}.")
        return RealApplyRollbackResult(approval_id, True, False, path, "Rollback refused because the file could not be removed.", type(exc).__name__)
    update_file_approval_real_apply(
        approval_id,
        event_type="real_apply_rollback_completed",
        message="Rollback removed only the Eva-created file.",
        real_apply_rollback_status="rolled_back",
        real_apply_rollback_at=_now(),
    )
    record_file_approval_event(approval_id, "real_create_rollback_completed", "Rollback removed only the Eva-created file.")
    return RealApplyRollbackResult(approval_id, True, True, path, "Rollback removed only the Eva-created file.")


def format_real_apply_status() -> str:
    return "\n".join(
        [
            "FileAgent real apply status",
            "",
            "Mode: Phase 12L narrow real apply gate.",
            "Allowed now: create-new-text-file only; create new .md or .txt files only in docs/ or samples/ after exact approval confirmation.",
            "Blocked: overwrite, edit existing files, source/config/runtime writes, delete, move, rename, and broad apply.",
            "Verification: required after create.",
            "Rollback: only unchanged Eva-created files with rollback record.",
        ]
    )


def format_real_create_request(request: RealApplyRequest) -> str:
    lines = [
        "FileAgent real create request",
        "",
        f"Approval ID: {request.approval_id}",
        f"Path: {request.display_path}",
        f"Operation: {request.operation}",
        f"Status: {'ready' if request.allowed else 'blocked'}",
        f"Required confirmation phrase: {request.required_confirmation_phrase}",
        "",
        format_authority_decision(request.authority),
    ]
    if request.blockers:
        lines.append("Blockers:")
        lines.extend(f"- {item}" for item in request.blockers)
    lines.extend(["", "No file was created, edited, overwritten, deleted, moved, or renamed."])
    return "\n".join(lines)


def format_real_apply_result(result: RealApplyResult) -> str:
    lines = [
            "FileAgent real create result",
        "",
        f"Approval ID: {result.approval_id}",
        f"Path: {result.display_path}",
        f"Status: {'created by narrow real create-new-text-file operation' if result.ok else 'refused'}",
        result.summary,
    ]
    if result.error:
        lines.extend(["", "Reason:", result.error])
    if result.authority:
        lines.extend(["", format_authority_decision(result.authority)])
    return "\n".join(lines)


def format_real_apply_verification(result: RealApplyVerificationResult) -> str:
    return "\n".join(
        [
            "FileAgent real create verification",
            "",
            f"Approval ID: {result.approval_id}",
            f"Path: {result.display_path}",
            f"Verified: {'yes' if result.verified else 'no'}",
            f"Confidence: {result.confidence:.2f}",
            "",
            "Evidence:",
            result.evidence,
        ]
    )


def format_real_apply_rollback(result: RealApplyRollbackResult) -> str:
    lines = [
        "FileAgent real create rollback",
        "",
        f"Approval ID: {result.approval_id}",
        f"Path: {result.display_path}",
        f"Attempted: {'yes' if result.attempted else 'no'}",
        f"Success: {'yes' if result.success else 'no'}",
        result.summary,
    ]
    if result.error:
        lines.extend(["Reason:", result.error])
    return "\n".join(lines)


def _authority_for_request(approval_id: str, display_path: str, allowed: bool, reason: str) -> AuthorityDecision:
    if allowed:
        return allow_real_execution_decision(
            action_type="file.real_create_safe_text",
            action_category="local_write",
            capability_id="file.real_create_new_text_file",
            agent_name="FileAgent",
            target_resource=display_path,
            approval_id=approval_id,
            requires_approval=True,
            reason="Narrow real create-new-text-file is allowed after exact approval confirmation.",
            risk_level="high",
        )
    return block_real_execution_decision(
        action_type="file.real_create_safe_text",
        action_category="local_write",
        capability_id="file.real_create_new_text_file",
        agent_name="FileAgent",
        target_resource=display_path,
        approval_id=approval_id,
        reason="Narrow real create is blocked.",
        blocked_reason=reason,
        public_mode_allowed=False,
    )


def _verify_target(path: Path, expected_hash: str) -> bool:
    try:
        return _hash(path.read_text(encoding="utf-8")) == expected_hash
    except OSError:
        return False


def _hash(text: str) -> str:
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _dedupe(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        clean = str(item or "").strip()
        if clean and clean not in out:
            out.append(clean)
    return out
