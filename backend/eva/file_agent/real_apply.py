from __future__ import annotations

from dataclasses import dataclass

from .real_apply_executor import (
    RealApplyRequest,
    RealApplyResult,
    RealApplyRollbackResult,
    build_real_create_request_from_approval,
    format_real_apply_result,
    format_real_apply_rollback,
    format_real_apply_verification,
    rollback_real_create,
    verify_real_create,
)
from .real_apply_policy import RealApplyEligibility, format_real_apply_eligibility, format_real_apply_policy


@dataclass(frozen=True)
class RealApplyVerification:
    approval_id: str
    verified: bool
    confidence: float
    display_path: str
    evidence: str
    failure_reason: str | None = None


def evaluate_real_apply_eligibility(approval_id: str) -> RealApplyEligibility:
    from .real_apply_policy import evaluate_real_apply_eligibility as _evaluate

    return _evaluate(approval_id)


def build_real_apply_request_from_approval(approval_id: str, confirmation_phrase: str = "") -> RealApplyRequest:
    return build_real_create_request_from_approval(approval_id, confirmation_phrase=confirmation_phrase)


def create_real_text_file_from_approval(approval_id: str, confirmation_phrase: str) -> RealApplyResult:
    from .real_apply_executor import apply_real_create

    request = build_real_apply_request_from_approval(approval_id, confirmation_phrase)
    return apply_real_create(request)


def verify_real_text_file_apply(result_or_approval_id: RealApplyResult | str) -> RealApplyVerification:
    approval_id = result_or_approval_id.approval_id if isinstance(result_or_approval_id, RealApplyResult) else str(result_or_approval_id or "")
    result = verify_real_create(approval_id)
    return RealApplyVerification(
        approval_id=result.approval_id,
        verified=result.verified,
        confidence=result.confidence,
        display_path=result.display_path,
        evidence=result.evidence,
        failure_reason=result.failure_reason,
    )


def rollback_real_text_file_apply(apply_id_or_approval_id: str, confirmation_phrase: str) -> RealApplyRollbackResult:
    return rollback_real_create(apply_id_or_approval_id, confirmation_phrase=confirmation_phrase)


__all__ = [
    "RealApplyEligibility",
    "RealApplyRequest",
    "RealApplyResult",
    "RealApplyVerification",
    "RealApplyRollbackResult",
    "evaluate_real_apply_eligibility",
    "build_real_apply_request_from_approval",
    "create_real_text_file_from_approval",
    "verify_real_text_file_apply",
    "rollback_real_text_file_apply",
    "format_real_apply_policy",
    "format_real_apply_eligibility",
    "format_real_apply_result",
    "format_real_apply_verification",
    "format_real_apply_rollback",
]
