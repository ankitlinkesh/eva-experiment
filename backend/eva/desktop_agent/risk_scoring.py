from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .risk import evaluate_desktop_action_risk


class DesktopRiskLevel(StrEnum):
    LOW_STATUS_ONLY = "low_status_only"
    MEDIUM_FUTURE_OBSERVATION = "medium_future_observation"
    HIGH_APPROVAL_REQUIRED = "high_approval_required"
    CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED = "critical_explicit_confirmation_required"
    FORBIDDEN_LOCKED = "forbidden_locked"


class DesktopApprovalLevel(StrEnum):
    NONE_STATUS_ONLY = "none_status_only"
    USER_PREVIEW_REQUIRED = "user_preview_required"
    EXPLICIT_USER_CONFIRMATION_REQUIRED = "explicit_user_confirmation_required"
    ELEVATED_CONFIRMATION_REQUIRED = "elevated_confirmation_required"
    FORBIDDEN_NO_APPROVAL_AVAILABLE = "forbidden_no_approval_available"


@dataclass(frozen=True)
class DesktopRiskFactor:
    name: str
    level: DesktopRiskLevel
    points: int
    reason: str


@dataclass(frozen=True)
class DesktopRiskScore:
    points: int
    level: DesktopRiskLevel
    label: str


@dataclass(frozen=True)
class DesktopApprovalRequirement:
    level: DesktopApprovalLevel
    phrase: str
    reason: str
    available_now: bool


@dataclass(frozen=True)
class DesktopRiskContext:
    request: str
    action_type: str
    target_app: str
    target_window: str
    screen_sensitivity: str


@dataclass(frozen=True)
class DesktopRiskScoreResult:
    request: str
    context: DesktopRiskContext
    score: DesktopRiskScore
    factors: tuple[DesktopRiskFactor, ...]
    approval: DesktopApprovalRequirement
    execution_enabled: bool
    summary: str


RISK_FACTOR_NAMES: tuple[str, ...] = (
    "action_type",
    "target_app",
    "target_window",
    "screen_sensitivity",
    "credential_or_secret_risk",
    "financial_or_payment_risk",
    "messaging_or_external_send_risk",
    "file_system_risk",
    "system_settings_risk",
    "terminal_or_code_execution_risk",
    "irreversibility",
    "unknown_context",
)


def score_desktop_action_risk(request: str) -> DesktopRiskScoreResult:
    cleaned = _clean_request(request)
    action = evaluate_desktop_action_risk(cleaned)
    context = DesktopRiskContext(
        request=cleaned,
        action_type=action.action_type,
        target_app=_target_app_hint(cleaned),
        target_window="not inspected",
        screen_sensitivity=_screen_sensitivity(cleaned),
    )
    factors = _risk_factors(cleaned, action.action_type)
    points = min(100, sum(factor.points for factor in factors))
    level = _level_for_points(points, cleaned)
    score = DesktopRiskScore(points=points, level=level, label=_label_for(level))
    approval = _approval_for_level(level, cleaned)
    return DesktopRiskScoreResult(
        request=cleaned,
        context=context,
        score=score,
        factors=factors,
        approval=approval,
        execution_enabled=False,
        summary="Desktop action risk scoring is status-only. Real desktop execution is locked.",
    )


def list_high_risk_desktop_actions() -> tuple[str, ...]:
    return (
        "mouse clicks, drags, and coordinate targeting",
        "typing into apps, password fields, or message boxes",
        "hotkeys and shortcuts that can submit, save, close, or delete",
        "clipboard reads or writes",
        "app launch/focus and file dialog workflows",
        "message sending, posting, uploading, payment, and login contexts",
        "terminal, shell, package, code execution, and system settings",
    )


def _risk_factors(text: str, action_type: str) -> tuple[DesktopRiskFactor, ...]:
    factors: list[DesktopRiskFactor] = []
    if action_type in {"mouse_click_preview", "mouse_drag_preview", "keyboard_type_preview", "hotkey_preview", "clipboard_read_preview", "clipboard_write_preview", "app_launch_preview", "file_dialog_preview"}:
        factors.append(DesktopRiskFactor("action_type", DesktopRiskLevel.HIGH_APPROVAL_REQUIRED, 35, f"{action_type} can change visible desktop state."))
    elif action_type == "screen_observation_preview":
        factors.append(DesktopRiskFactor("screen_sensitivity", DesktopRiskLevel.MEDIUM_FUTURE_OBSERVATION, 25, "Screen observation may expose private visible content."))
    elif action_type == "terminal_preview":
        factors.append(DesktopRiskFactor("terminal_or_code_execution_risk", DesktopRiskLevel.FORBIDDEN_LOCKED, 100, "Terminal, shell, package, and code execution are locked."))
    else:
        factors.append(DesktopRiskFactor("unknown_context", DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, 50, "Unknown desktop context cannot be safely executed."))

    if any(term in text for term in ("password", "credential", "secret", "token", "cookie")):
        factors.append(DesktopRiskFactor("credential_or_secret_risk", DesktopRiskLevel.FORBIDDEN_LOCKED, 80, "Credential, secret, token, and session contexts are forbidden."))
    if any(term in text for term in ("pay", "payment", "bank", "card", "checkout")):
        factors.append(DesktopRiskFactor("financial_or_payment_risk", DesktopRiskLevel.FORBIDDEN_LOCKED, 80, "Payment and banking actions are locked."))
    if any(term in text for term in ("send", "message", "whatsapp", "email", "post", "submit")):
        factors.append(DesktopRiskFactor("messaging_or_external_send_risk", DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, 45, "External messages, posts, and submissions require future explicit confirmation."))
    if any(term in text for term in ("upload", "download", "file", "folder", "delete", "rename", "move")):
        factors.append(DesktopRiskFactor("file_system_risk", DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, 45, "File and upload/download contexts need future path and privacy gates."))
    if any(term in text for term in ("settings", "registry", "control panel", "system")):
        factors.append(DesktopRiskFactor("system_settings_risk", DesktopRiskLevel.FORBIDDEN_LOCKED, 80, "System settings changes remain locked."))
    if any(term in text for term in ("terminal", "shell", "powershell", "cmd", "install", "package", "code execution")):
        factors.append(DesktopRiskFactor("terminal_or_code_execution_risk", DesktopRiskLevel.FORBIDDEN_LOCKED, 100, "Terminal/package/code execution remains locked."))
    if any(term in text for term in ("delete", "submit", "send", "pay", "install", "shutdown")):
        factors.append(DesktopRiskFactor("irreversibility", DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, 35, "The request may be hard to undo after execution."))
    if "not inspected" in text or not text:
        factors.append(DesktopRiskFactor("unknown_context", DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, 30, "The context is unknown."))
    return tuple(factors)


def _level_for_points(points: int, text: str) -> DesktopRiskLevel:
    if any(term in text for term in ("terminal", "shell", "powershell", "cmd", "install", "package", "password", "credential", "secret", "token", "cookie", "payment", "bank", "card", "settings", "registry")):
        return DesktopRiskLevel.FORBIDDEN_LOCKED
    if points >= 70:
        return DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED
    if points >= 35:
        return DesktopRiskLevel.HIGH_APPROVAL_REQUIRED
    if points >= 20:
        return DesktopRiskLevel.MEDIUM_FUTURE_OBSERVATION
    return DesktopRiskLevel.LOW_STATUS_ONLY


def _approval_for_level(level: DesktopRiskLevel, text: str) -> DesktopApprovalRequirement:
    if level == DesktopRiskLevel.LOW_STATUS_ONLY:
        return DesktopApprovalRequirement(DesktopApprovalLevel.NONE_STATUS_ONLY, "none", "Status-only output is allowed.", False)
    if level == DesktopRiskLevel.MEDIUM_FUTURE_OBSERVATION:
        return DesktopApprovalRequirement(DesktopApprovalLevel.USER_PREVIEW_REQUIRED, "future screen preview permission", "Future observation would need an explicit user-commanded preview gate.", False)
    if level == DesktopRiskLevel.HIGH_APPROVAL_REQUIRED:
        return DesktopApprovalRequirement(DesktopApprovalLevel.EXPLICIT_USER_CONFIRMATION_REQUIRED, "future exact action confirmation", "Future execution would need confirmation, target verification, audit, and repair policy.", False)
    if level == DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED:
        return DesktopApprovalRequirement(DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, "future elevated confirmation", "Critical actions need stronger confirmation plus rollback/repair evidence before execution could be considered.", False)
    return DesktopApprovalRequirement(DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE, "not available", "This action class is locked and has no approval path in Phase 14E.", False)


def _target_app_hint(text: str) -> str:
    for app in ("terminal", "powershell", "cmd", "whatsapp", "email", "browser", "file explorer", "settings"):
        if app in text:
            return app
    return "not inspected"


def _screen_sensitivity(text: str) -> str:
    if any(term in text for term in ("password", "bank", "payment", "message", "email", "secret", "token")):
        return "sensitive context mentioned"
    return "not inspected"


def _label_for(level: DesktopRiskLevel) -> str:
    return level.value.replace("_", " ")


def _clean_request(request: str) -> str:
    text = " ".join(str(request or "").strip().lower().split())
    return text[:180] if text else "desktop risk score"
