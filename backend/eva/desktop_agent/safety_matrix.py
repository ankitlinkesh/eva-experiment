from __future__ import annotations

from dataclasses import dataclass

from .risk_scoring import DesktopApprovalLevel, DesktopRiskLevel


@dataclass(frozen=True)
class DesktopSafetyMatrixDecision:
    action_type: str
    risk_level: DesktopRiskLevel
    approval_level: DesktopApprovalLevel
    execution_status: str
    reason: str


@dataclass(frozen=True)
class DesktopRiskMatrix:
    status: str
    decisions: tuple[DesktopSafetyMatrixDecision, ...]
    forbidden_action_classes: tuple[str, ...]
    readiness_gaps: tuple[str, ...]
    next_phase: str


def build_desktop_safety_matrix() -> DesktopRiskMatrix:
    decisions = (
        DesktopSafetyMatrixDecision("status_only", DesktopRiskLevel.LOW_STATUS_ONLY, DesktopApprovalLevel.NONE_STATUS_ONLY, "allowed as text", "Status and policy output only."),
        DesktopSafetyMatrixDecision("screen_observation_preview", DesktopRiskLevel.MEDIUM_FUTURE_OBSERVATION, DesktopApprovalLevel.USER_PREVIEW_REQUIRED, "locked", "Future observation needs an explicit local screen gate."),
        DesktopSafetyMatrixDecision("mouse_click_preview", DesktopRiskLevel.HIGH_APPROVAL_REQUIRED, DesktopApprovalLevel.EXPLICIT_USER_CONFIRMATION_REQUIRED, "locked", "Clicking needs verified target confidence and audit."),
        DesktopSafetyMatrixDecision("keyboard_type_preview", DesktopRiskLevel.HIGH_APPROVAL_REQUIRED, DesktopApprovalLevel.EXPLICIT_USER_CONFIRMATION_REQUIRED, "locked", "Typing needs focused-field verification and external-send guards."),
        DesktopSafetyMatrixDecision("hotkey_preview", DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, "locked", "Hotkeys can submit, close, save, delete, or change state."),
        DesktopSafetyMatrixDecision("clipboard_read_preview", DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, "locked", "Clipboard may contain private data."),
        DesktopSafetyMatrixDecision("clipboard_write_preview", DesktopRiskLevel.HIGH_APPROVAL_REQUIRED, DesktopApprovalLevel.EXPLICIT_USER_CONFIRMATION_REQUIRED, "locked", "Clipboard writes need user intent and audit."),
        DesktopSafetyMatrixDecision("app_launch_preview", DesktopRiskLevel.HIGH_APPROVAL_REQUIRED, DesktopApprovalLevel.EXPLICIT_USER_CONFIRMATION_REQUIRED, "locked", "App launch/focus needs app-risk policy."),
        DesktopSafetyMatrixDecision("file_dialog_preview", DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, "locked", "File dialogs need path and privacy gates."),
        DesktopSafetyMatrixDecision("terminal_preview", DesktopRiskLevel.FORBIDDEN_LOCKED, DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE, "forbidden", "Terminal, shell, package, and code execution stay locked."),
    )
    return DesktopRiskMatrix(
        status="risk/status only",
        decisions=decisions,
        forbidden_action_classes=(
            "terminal, shell, package, and code execution",
            "credential, secret, token, cookie, and password handling",
            "payment, banking, and system settings workflows",
            "silent external send/post/submit workflows",
        ),
        readiness_gaps=(
            "no real screen/window/app observation",
            "no verified UI target model",
            "no human approval session for desktop actions",
            "no action audit, verification, repair, or rollback executor",
        ),
        next_phase="Human Approval Model for Desktop Actions",
    )
