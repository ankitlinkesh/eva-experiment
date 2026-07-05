from __future__ import annotations

from .models import DesktopScreenCaptureGate, DesktopScreenObservationPreview
from .screen_policy import BLOCKED_SCREEN_OBSERVATION_ACTIONS


def create_screen_observation_preview() -> DesktopScreenObservationPreview:
    return DesktopScreenObservationPreview(
        title="Desktop screen observation policy preview",
        mode="policy_preview_only",
        real_capture_performed=False,
        schema_fields=(
            "observation_reason",
            "task_id",
            "sensitive_screen_category",
            "redaction_applied",
            "local_summary",
            "verification_target",
            "audit_event_id",
        ),
        blocked_fields=(
            "screen pixels",
            "screenshots",
            "OCR text",
            "raw image data",
            "window handles or titles from real inspection",
            "credentials, tokens, cookies, passwords, browser sessions, and private content",
        ),
        notes=(
            "This is a schema/policy preview only.",
            "No screen capture, screenshot, OCR, image analysis, window inspection, or active app detection was performed.",
            "Future capture would require explicit user command, sensitive-screen checks, local redaction, and separate approval for cloud sharing.",
        ),
    )


def get_desktop_screen_capture_gate() -> DesktopScreenCaptureGate:
    return DesktopScreenCaptureGate(
        status="locked",
        capture_allowed_now=False,
        exact_user_command_required=True,
        confirmation_required=True,
        override_required_for_sensitive_screens=True,
        blocked_now=BLOCKED_SCREEN_OBSERVATION_ACTIONS,
        future_requirements=(
            "explicit user command for each observation",
            "clear reason and task target",
            "sensitive-screen classification before capture",
            "local-only capture storage by default",
            "redaction before summary or sharing",
            "separate confirmation before any cloud vision or cloud summary",
            "WorkSession audit event and verification result",
        ),
        summary="Screen capture gate is locked. Phase 14C defines policy only; it does not capture screens or take screenshots.",
    )
