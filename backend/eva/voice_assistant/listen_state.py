from __future__ import annotations

from .voice_policy import boundary_lines


def listen_state_policy_text() -> str:
    return "\n".join(
        [
            "Voice listen-state policy",
            *boundary_lines(),
            "Current state: disabled.",
            "Listen state is mock/status only.",
            "No always-listening mode or real background listener exists.",
            "No microphone permission request or audio-device polling occurs.",
            "Available safe transitions: disabled -> idle -> wake_preview -> listening_preview -> stopped_safely.",
            "Stop and disable states are always available.",
        ]
    )
