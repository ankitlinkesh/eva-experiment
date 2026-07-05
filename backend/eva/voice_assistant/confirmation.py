from __future__ import annotations

from .models import VoiceConfirmationPreview
from .voice_policy import boundary_lines


def evaluate_confirmation_preview(confirmation_text: str, action_summary: str) -> VoiceConfirmationPreview:
    received = str(confirmation_text or "").strip().lower() in {"confirm", "yes, confirm", "i confirm"}
    return VoiceConfirmationPreview(
        confirmation_received=received,
        action_summary=str(action_summary or "unspecified future action"),
        execution_allowed=False,
        decision="Confirmation preview only; an existing implemented gate must independently accept any future action.",
    )


def confirmation_policy_text() -> str:
    return "\n".join(
        [
            "Voice confirmation policy",
            *boundary_lines(),
            "High-risk future actions require a confirmation preview.",
            "Confirmation alone does not execute or authorize anything.",
            "An existing implemented execution gate must independently accept any future action.",
            "Phase 22 exposes confirmation status and policy only.",
        ]
    )
