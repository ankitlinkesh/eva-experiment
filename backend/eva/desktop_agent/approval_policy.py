from __future__ import annotations

from dataclasses import dataclass

from .approval_model import DesktopApprovalLevel


@dataclass(frozen=True)
class DesktopForbiddenActionClass:
    action_class: str
    reason: str
    approval_available: bool


@dataclass(frozen=True)
class DesktopApprovalPolicy:
    status: str
    approval_levels: tuple[DesktopApprovalLevel, ...]
    approval_states: tuple[str, ...]
    real_execution_unlocked: bool
    forbidden_classes: tuple[DesktopForbiddenActionClass, ...]
    expiration_seconds: int
    summary: str


def get_desktop_approval_policy() -> DesktopApprovalPolicy:
    return DesktopApprovalPolicy(
        status="approval-policy/status only",
        approval_levels=tuple(DesktopApprovalLevel),
        approval_states=(
            "not_required_status_only",
            "preview_only",
            "pending_future_approval",
            "approved_for_future_gate_only",
            "denied",
            "expired",
            "blocked",
            "forbidden",
        ),
        real_execution_unlocked=False,
        forbidden_classes=list_desktop_forbidden_action_classes(),
        expiration_seconds=120,
        summary="Desktop approvals are previews only and do not unlock real desktop execution.",
    )


def list_desktop_forbidden_action_classes() -> tuple[DesktopForbiddenActionClass, ...]:
    return (
        DesktopForbiddenActionClass("credentials_or_secrets_entry", "Credential, secret, token, cookie, and password handling is forbidden.", False),
        DesktopForbiddenActionClass("payment_or_financial_action", "Payment, banking, and financial desktop actions are locked.", False),
        DesktopForbiddenActionClass("external_message_send", "Sending external messages/posts/submissions requires future gates and is not executable now.", False),
        DesktopForbiddenActionClass("destructive_file_operation", "Destructive file actions remain outside DesktopAgent approval.", False),
        DesktopForbiddenActionClass("terminal_or_code_execution", "Terminal, shell, package, and code execution are forbidden here.", False),
        DesktopForbiddenActionClass("system_settings_change", "System settings and registry changes are locked.", False),
        DesktopForbiddenActionClass("unknown_screen_context", "Unknown screen context requires elevated future handling and cannot be approved now.", False),
        DesktopForbiddenActionClass("hidden_or_unverified_target", "Hidden or unverified UI targets cannot be approved.", False),
        DesktopForbiddenActionClass("bypass_safety_request", "Requests to bypass safety are refused.", False),
    )
