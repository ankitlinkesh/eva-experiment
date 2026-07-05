from __future__ import annotations

from .models import DesktopWindowStatusPreview


def create_window_status_preview() -> DesktopWindowStatusPreview:
    return DesktopWindowStatusPreview(
        title="Desktop window status schema preview",
        mode="preview_only",
        real_window_enumeration=False,
        schema_fields=(
            "window_label",
            "app_label",
            "visibility_state",
            "privacy_sensitivity",
            "target_confidence",
            "allowed_future_observation",
            "blocked_future_actions",
            "verification_evidence",
        ),
        blocked_fields=(
            "real window handles",
            "real window titles",
            "real screen bounds",
            "screen pixels or screenshots",
            "private document, chat, email, browser, credential, or session contents",
        ),
        notes=(
            "The schema is a future DesktopAgent observation contract.",
            "No windows were enumerated, focused, read, or controlled.",
        ),
    )
