from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DesktopActionRiskLevel(StrEnum):
    LOW_STATUS_ONLY = "low_status_only"
    MEDIUM_FUTURE_OBSERVATION = "medium_future_observation"
    HIGH_USER_CONFIRMATION_REQUIRED = "high_user_confirmation_required"
    CRITICAL_BLOCKED = "critical_blocked"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True)
class DesktopActionRisk:
    action: str
    action_type: str
    level: DesktopActionRiskLevel
    executable_now: bool
    reason: str
    approval_required: str
    blocked_now: bool


def evaluate_desktop_action_risk(action: str) -> DesktopActionRisk:
    normalized = _normalize(action)
    action_type = _action_type_for(normalized)
    if normalized in {"status", "policy", "readiness", "approvals"}:
        return DesktopActionRisk(
            normalized,
            action_type,
            DesktopActionRiskLevel.LOW_STATUS_ONLY,
            False,
            "Status, policy, readiness, and approval previews are allowed as text only.",
            "none",
            False,
        )
    if normalized == "screen observation":
        return DesktopActionRisk(
            normalized,
            action_type,
            DesktopActionRiskLevel.MEDIUM_FUTURE_OBSERVATION,
            False,
            "Screen observation can be described as future policy, but no screen is captured or read now.",
            "future explicit screen observation gate",
            True,
        )
    if normalized in {"mouse move", "mouse click", "mouse drag", "keyboard type", "hotkey", "clipboard read", "clipboard write", "app launch", "file dialog"}:
        return DesktopActionRisk(
            normalized,
            action_type,
            DesktopActionRiskLevel.CRITICAL_BLOCKED,
            False,
            "Interactive desktop actions are blocked in Phase 14D and can only be previewed.",
            "future explicit confirmation, target verification, audit, and rollback/repair gate",
            True,
        )
    if normalized in {"terminal", "shell", "package", "credential", "secret"}:
        return DesktopActionRisk(
            normalized,
            action_type,
            DesktopActionRiskLevel.FORBIDDEN,
            False,
            "Terminal/package execution and credential or secret access are forbidden for DesktopAgent dry-run.",
            "not overridable in this phase",
            True,
        )
    return DesktopActionRisk(
        normalized or "unknown",
        "unknown_preview",
        DesktopActionRiskLevel.CRITICAL_BLOCKED,
        False,
        "Unknown desktop actions are blocked and can only be described as dry-run text.",
        "future action classification gate",
        True,
    )


def _normalize(action: str) -> str:
    text = str(action or "").strip().lower().replace("-", " ").replace("_", " ")
    text = " ".join(text.split())
    if not text:
        return "unknown"
    if any(term in text for term in ("terminal", "shell", "cmd", "powershell", "command line")):
        return "terminal"
    if any(term in text for term in ("package", "install", "pip ", "npm ")):
        return "package"
    if any(term in text for term in ("password", "credential", "token", "cookie", "secret")):
        return "credential"
    if any(term in text for term in ("screen", "screenshot", "observe", "read my screen")):
        return "screen observation"
    if "drag" in text:
        return "mouse drag"
    if "click" in text or "button" in text:
        return "mouse click"
    if "move" in text and "mouse" in text:
        return "mouse move"
    if any(term in text for term in ("type", "write into", "enter text")):
        return "keyboard type"
    if any(term in text for term in ("hotkey", "shortcut", "ctrl", "alt", "shift", "press")):
        return "hotkey"
    if "clipboard" in text and any(term in text for term in ("read", "paste", "get")):
        return "clipboard read"
    if "clipboard" in text and any(term in text for term in ("write", "copy", "set")):
        return "clipboard write"
    if any(term in text for term in ("open app", "launch app", "start app", "open an app")):
        return "app launch"
    if any(term in text for term in ("file dialog", "save dialog", "open dialog", "upload dialog")):
        return "file dialog"
    if text in {"status", "policy", "readiness", "approvals"}:
        return text
    return text


def _action_type_for(action: str) -> str:
    mapping = {
        "mouse move": "mouse_move_preview",
        "mouse click": "mouse_click_preview",
        "mouse drag": "mouse_drag_preview",
        "keyboard type": "keyboard_type_preview",
        "hotkey": "hotkey_preview",
        "clipboard read": "clipboard_read_preview",
        "clipboard write": "clipboard_write_preview",
        "app launch": "app_launch_preview",
        "file dialog": "file_dialog_preview",
        "terminal": "terminal_preview",
        "shell": "terminal_preview",
        "package": "terminal_preview",
        "screen observation": "screen_observation_preview",
    }
    return mapping.get(action, "unknown_preview")
