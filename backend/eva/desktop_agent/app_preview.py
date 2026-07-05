from __future__ import annotations

from .models import DesktopActiveContextPreview, DesktopAppStatusPreview


def create_app_status_preview() -> DesktopAppStatusPreview:
    return DesktopAppStatusPreview(
        title="Desktop app status schema preview",
        mode="preview_only",
        real_app_inspection=False,
        schema_fields=(
            "app_label",
            "app_category",
            "risk_level",
            "visible_state_summary",
            "privacy_sensitivity",
            "allowed_future_actions",
            "blocked_future_actions",
            "verification_evidence",
        ),
        blocked_fields=(
            "real process list",
            "real app contents",
            "secret, token, cookie, password, and browser-session data",
            "private document or chat contents",
        ),
        notes=(
            "The schema is design-only in Phase 14B.",
            "No app was opened, focused, inspected, enumerated, or controlled.",
        ),
    )


def create_active_context_preview() -> DesktopActiveContextPreview:
    return DesktopActiveContextPreview(
        title="Desktop active context schema preview",
        mode="preview_only",
        real_active_app_detection=False,
        schema_fields=(
            "active_app_label",
            "active_window_label",
            "task_target",
            "privacy_risk",
            "safe_observation_summary",
            "needs_user_permission",
            "verification_target",
        ),
        blocked_fields=(
            "real active app detection",
            "real active window title",
            "screen pixels or screenshots",
            "private screen text",
            "credentials, tokens, cookies, passwords, and browser sessions",
        ),
        notes=(
            "Active context is a future schema only.",
            "No active app, window, screen, or private desktop state was detected.",
        ),
    )
