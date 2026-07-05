from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .risk_scoring import DesktopRiskLevel, score_desktop_action_risk


class DesktopApprovalLevel(StrEnum):
    NONE_STATUS_ONLY = "none_status_only"
    PREVIEW_REQUIRED = "preview_required"
    EXPLICIT_CONFIRMATION_REQUIRED = "explicit_confirmation_required"
    ELEVATED_CONFIRMATION_REQUIRED = "elevated_confirmation_required"
    REPEATED_CONFIRMATION_REQUIRED = "repeated_confirmation_required"
    FORBIDDEN_NO_APPROVAL_AVAILABLE = "forbidden_no_approval_available"


class DesktopApprovalState(StrEnum):
    NOT_REQUIRED_STATUS_ONLY = "not_required_status_only"
    PREVIEW_ONLY = "preview_only"
    PENDING_FUTURE_APPROVAL = "pending_future_approval"
    APPROVED_FOR_FUTURE_GATE_ONLY = "approved_for_future_gate_only"
    DENIED = "denied"
    EXPIRED = "expired"
    BLOCKED = "blocked"
    FORBIDDEN = "forbidden"


class DesktopConfirmationPhraseType(StrEnum):
    NORMAL_PREVIEW_CONFIRMATION = "normal_preview_confirmation"
    EXPLICIT_DESKTOP_ACTION_CONFIRMATION = "explicit_desktop_action_confirmation"
    ELEVATED_SENSITIVE_ACTION_CONFIRMATION = "elevated_sensitive_action_confirmation"
    FORBIDDEN_ACTION_REFUSAL = "forbidden_action_refusal"


@dataclass(frozen=True)
class DesktopApprovalExpiration:
    status: str
    future_ttl_seconds: int
    note: str


@dataclass(frozen=True)
class DesktopConfirmationPhrase:
    phrase_type: DesktopConfirmationPhraseType
    preview_phrase: str
    note: str
    unlocks_execution: bool


@dataclass(frozen=True)
class DesktopApprovalDecisionPreview:
    approval_level: DesktopApprovalLevel
    state: DesktopApprovalState
    reason: str
    confirmation_phrase: DesktopConfirmationPhrase
    expiration: DesktopApprovalExpiration
    execution_unlocked: bool


@dataclass(frozen=True)
class DesktopApprovalRequestPreview:
    request: str
    risk_level: str
    decision: DesktopApprovalDecisionPreview
    future_gate_only: bool
    summary: str


@dataclass(frozen=True)
class DesktopApprovalGateResult:
    request: str
    allowed_now: bool
    gate_status: str
    reason: str


def preview_desktop_approval_request(request: str) -> DesktopApprovalRequestPreview:
    cleaned = _clean_request(request)
    risk = score_desktop_action_risk(cleaned)
    level = _approval_level_for(cleaned, risk.score.level)
    state = _state_for(level)
    phrase = _phrase_for(cleaned, level)
    expiration = DesktopApprovalExpiration(
        status="future policy only",
        future_ttl_seconds=120,
        note="Future desktop approvals would expire quickly and require visible task context.",
    )
    decision = DesktopApprovalDecisionPreview(
        approval_level=level,
        state=state,
        reason=_reason_for(cleaned, level),
        confirmation_phrase=phrase,
        expiration=expiration,
        execution_unlocked=False,
    )
    return DesktopApprovalRequestPreview(
        request=cleaned,
        risk_level=risk.score.level.value,
        decision=decision,
        future_gate_only=True,
        summary="Approval preview only. It does not unlock real desktop execution.",
    )


def evaluate_desktop_approval_gate(request: str) -> DesktopApprovalGateResult:
    preview = preview_desktop_approval_request(request)
    return DesktopApprovalGateResult(
        request=preview.request,
        allowed_now=False,
        gate_status=preview.decision.state.value,
        reason="Desktop approvals are policy/status previews only and do not unlock execution.",
    )


def _approval_level_for(text: str, risk_level: DesktopRiskLevel) -> DesktopApprovalLevel:
    if _forbidden_context(text):
        return DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE
    if any(term in text for term in ("unknown", "hidden", "unverified", "screen context")):
        return DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED
    if any(term in text for term in ("send", "message", "post", "submit", "upload", "delete", "destructive", "file")):
        return DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED
    if risk_level == DesktopRiskLevel.LOW_STATUS_ONLY:
        return DesktopApprovalLevel.NONE_STATUS_ONLY
    if risk_level == DesktopRiskLevel.MEDIUM_FUTURE_OBSERVATION:
        return DesktopApprovalLevel.PREVIEW_REQUIRED
    if risk_level == DesktopRiskLevel.HIGH_APPROVAL_REQUIRED:
        return DesktopApprovalLevel.EXPLICIT_CONFIRMATION_REQUIRED
    if risk_level == DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED:
        return DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED
    return DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE


def _state_for(level: DesktopApprovalLevel) -> DesktopApprovalState:
    if level == DesktopApprovalLevel.NONE_STATUS_ONLY:
        return DesktopApprovalState.NOT_REQUIRED_STATUS_ONLY
    if level == DesktopApprovalLevel.PREVIEW_REQUIRED:
        return DesktopApprovalState.PREVIEW_ONLY
    if level in {DesktopApprovalLevel.EXPLICIT_CONFIRMATION_REQUIRED, DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, DesktopApprovalLevel.REPEATED_CONFIRMATION_REQUIRED}:
        return DesktopApprovalState.PENDING_FUTURE_APPROVAL
    return DesktopApprovalState.FORBIDDEN


def _phrase_for(text: str, level: DesktopApprovalLevel) -> DesktopConfirmationPhrase:
    if level == DesktopApprovalLevel.NONE_STATUS_ONLY:
        return DesktopConfirmationPhrase(DesktopConfirmationPhraseType.NORMAL_PREVIEW_CONFIRMATION, "no phrase required", "Status-only output does not need confirmation.", False)
    if level == DesktopApprovalLevel.PREVIEW_REQUIRED:
        return DesktopConfirmationPhrase(DesktopConfirmationPhraseType.NORMAL_PREVIEW_CONFIRMATION, "preview desktop action only", "Future preview confirmation would not execute actions.", False)
    if level == DesktopApprovalLevel.EXPLICIT_CONFIRMATION_REQUIRED:
        return DesktopConfirmationPhrase(DesktopConfirmationPhraseType.EXPLICIT_DESKTOP_ACTION_CONFIRMATION, "confirm desktop action preview", "Future explicit confirmation would still be gate-only in this phase.", False)
    if level in {DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, DesktopApprovalLevel.REPEATED_CONFIRMATION_REQUIRED}:
        return DesktopConfirmationPhrase(DesktopConfirmationPhraseType.ELEVATED_SENSITIVE_ACTION_CONFIRMATION, "confirm elevated desktop action preview", "Sensitive desktop approval remains future-gated and non-executing.", False)
    return DesktopConfirmationPhrase(DesktopConfirmationPhraseType.FORBIDDEN_ACTION_REFUSAL, "not available", "Forbidden desktop action classes cannot be approved.", False)


def _reason_for(text: str, level: DesktopApprovalLevel) -> str:
    if level == DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE:
        return "This desktop action class is forbidden or locked and has no approval path now."
    if level == DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED:
        return "This would require elevated future confirmation, verified target context, audit, and rollback/repair policy."
    if level == DesktopApprovalLevel.EXPLICIT_CONFIRMATION_REQUIRED:
        return "This would require explicit future confirmation and verified UI target context."
    if level == DesktopApprovalLevel.PREVIEW_REQUIRED:
        return "Only a preview/status explanation is available now."
    return "Status-only output does not require approval."


def _forbidden_context(text: str) -> bool:
    return any(term in text for term in ("password", "credential", "secret", "token", "cookie", "payment", "financial", "bank", "terminal", "shell", "powershell", "cmd", "code execution", "system settings", "registry", "bypass safety"))


def _clean_request(request: str) -> str:
    text = " ".join(str(request or "").strip().lower().split())
    return text[:180] if text else "desktop approval preview"
