from __future__ import annotations

from .voice_policy import boundary_lines


def response_policy_text() -> str:
    return "\n".join(
        [
            "Voice response policy",
            *boundary_lines(),
            "Response mode is text preview only.",
            "Only a final safe response preview is surfaced.",
            "Partial transcript, activity, tool, and status events are never treated as speech output.",
            "Unsafe input receives a refusal or blocked preview.",
        ]
    )
