from __future__ import annotations

from .voice_policy import boundary_lines


def wake_policy_text() -> str:
    return "\n".join(
        [
            "Voice wake policy",
            *boundary_lines(),
            "Wake word: Eva (policy metadata only).",
            "Wake detection is not connected to a microphone or background listener.",
            "A wake preview may only transition to a mock listening preview.",
            "Disable and stop requests transition to stopped_safely.",
        ]
    )
