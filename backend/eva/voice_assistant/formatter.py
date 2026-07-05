from __future__ import annotations

from .confirmation import confirmation_policy_text
from .listen_state import listen_state_policy_text
from .provider_policy import provider_policy_text
from .response_policy import response_policy_text
from .routing_preview import build_voice_route_preview
from .status import get_voice_assistant_status
from .transcript_safety import transcript_safety_policy_text
from .voice_policy import boundary_lines, voice_policy_text
from .wake_policy import wake_policy_text


def format_voice_status() -> str:
    status = get_voice_assistant_status()
    return "\n".join(
        [
            "Voice Assistant Foundation status",
            *boundary_lines(),
            f"Status: {status.status}.",
            f"Mode: {status.mode}.",
            f"Lifecycle state: {status.lifecycle_state}.",
            f"Transcript safety: {status.transcript_safety_status}.",
            f"Confirmation policy: {status.confirmation_policy}.",
            f"Execution gate integration: {status.execution_gate_integration}.",
            f"Readiness: {status.readiness}.",
            f"Next phase: {status.next_phase}.",
        ]
    )


def format_voice_policy() -> str:
    return "\n\n".join([voice_policy_text(), response_policy_text()])


def format_voice_providers() -> str:
    return provider_policy_text()


def format_voice_listen_state() -> str:
    return "\n\n".join([listen_state_policy_text(), wake_policy_text()])


def format_voice_transcript_safety() -> str:
    return transcript_safety_policy_text()


def format_voice_route_preview() -> str:
    return build_voice_route_preview().format()


def format_voice_confirmations() -> str:
    return confirmation_policy_text()


def format_voice_readiness() -> str:
    return "\n".join(
        [
            "Voice Assistant Foundation readiness",
            *boundary_lines(),
            "Transcript safety, provider policy, wake/listen state policy, and confirmation preview are implemented.",
            "Agent-loop, workflow-planner, and execution-gate awareness is preview-only.",
            "No provider SDK or package is installed or invoked.",
            "No arbitrary filesystem read or write is introduced.",
            "Ready for Phase 22 local/mock status and preview use.",
            "Next phase: Phase 23 AI OS / Control Center Upgrade.",
        ]
    )
