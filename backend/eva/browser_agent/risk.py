from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class BrowserActionRiskLevel(StrEnum):
    LOW_STATUS_ONLY = "low_status_only"
    MEDIUM_READONLY_FUTURE = "medium_readonly_future"
    HIGH_USER_CONFIRMATION_REQUIRED = "high_user_confirmation_required"
    CRITICAL_BLOCKED = "critical_blocked"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class BrowserActionRisk:
    action: str
    action_type: str
    level: BrowserActionRiskLevel
    executable_now: bool
    reason: str
    approval_required: str
    blocked_now: bool


def evaluate_browser_action_risk(action: str) -> BrowserActionRisk:
    normalized = _normalize(action)
    action_type = _action_type_for(normalized)
    if normalized in {"status", "policy", "readiness", "approvals"}:
        return BrowserActionRisk(normalized, action_type, BrowserActionRiskLevel.LOW_STATUS_ONLY, False, "Status and policy views are allowed as text only.", "none", False)
    if normalized in {"navigate", "open", "website", "search", "extract", "screenshot"}:
        return BrowserActionRisk(normalized, action_type, BrowserActionRiskLevel.MEDIUM_READONLY_FUTURE, False, "This can be planned as a preview, but no browser action is executed now.", "future read-only gate", True)
    if normalized in {"click", "type", "submit", "login", "upload", "download", "payment"}:
        return BrowserActionRisk(normalized, action_type, BrowserActionRiskLevel.CRITICAL_BLOCKED, False, "Interactive or external browser actions are blocked in Phase 13D.", "future explicit confirmation and verification gate", True)
    if normalized in {"cookie", "cookies", "localstorage", "profile", "password", "session", "token"}:
        return BrowserActionRisk(normalized, action_type, BrowserActionRiskLevel.FORBIDDEN, False, "Browser private/session data access is forbidden.", "not overridable in this phase", True)
    return BrowserActionRisk(normalized or "unknown", "unknown_preview", BrowserActionRiskLevel.CRITICAL_BLOCKED, False, "Unknown browser actions are blocked and can only be described as dry-run text.", "future classification gate", True)


def _normalize(action: str) -> str:
    text = str(action or "").strip().lower().replace("-", " ").replace("_", " ")
    for candidate in ("local storage", "localstorage"):
        if candidate in text:
            return "localstorage"
    for candidate in ("navigate", "open", "website", "search", "click", "type", "submit", "login", "payment", "upload", "download", "extract", "screenshot", "cookie", "profile", "password", "session", "token", "status", "policy", "readiness", "approvals"):
        if candidate in text:
            return candidate
    return " ".join(text.split()) or "unknown"


def _action_type_for(action: str) -> str:
    mapping = {
        "navigate": "navigate_preview",
        "open": "navigate_preview",
        "website": "navigate_preview",
        "search": "search_preview",
        "click": "click_preview",
        "type": "type_preview",
        "submit": "submit_preview",
        "login": "login_preview",
        "payment": "login_preview",
        "upload": "upload_preview",
        "download": "download_preview",
        "extract": "extract_preview",
        "screenshot": "screenshot_preview",
    }
    return mapping.get(action, "unknown_preview")
