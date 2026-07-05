from __future__ import annotations

from .models import TranscriptSafetyResult, VoiceConfirmationPreview, VoiceSessionPreview
from .voice_policy import boundary_lines


def format_transcript_safety(result: TranscriptSafetyResult) -> str:
    flags = ", ".join(result.flags) if result.flags else "none"
    return "\n".join(
        [
            "Voice transcript safety result",
            *boundary_lines(),
            f"Classification: {result.classification}.",
            f"Redaction status: {'redacted' if result.redacted else 'not required'}.",
            f"Safe transcript preview: {result.safe_transcript}",
            f"Safety flags: {flags}.",
            f"Blocked reason: {result.blocked_reason or 'none'}.",
        ]
    )


def format_confirmation_preview(result: VoiceConfirmationPreview) -> str:
    return "\n".join(
        [
            "Voice confirmation preview",
            *boundary_lines(),
            f"Confirmation received: {result.confirmation_received}.",
            f"Action summary: {result.action_summary}.",
            f"Execution allowed: {result.execution_allowed}.",
            f"Decision: {result.decision}",
        ]
    )


def format_voice_session_preview(preview: VoiceSessionPreview) -> str:
    return "\n".join(
        [
            "Voice route preview",
            *boundary_lines(),
            f"Voice session ID: {preview.voice_session_id}.",
            f"Current state: {preview.current_state}.",
            f"Mock input transcript: {preview.mock_input_transcript}",
            f"Transcript safety: {preview.transcript_safety_classification}.",
            f"Redaction status: {preview.redaction_status}.",
            f"Detected intent: {preview.detected_intent_summary}.",
            f"Selected route: {preview.selected_route_preview}.",
            f"Confirmation requirement: {preview.confirmation_requirement}.",
            f"Execution gate decision: {preview.execution_gate_decision_summary}.",
            f"Response mode: {preview.response_mode}.",
            f"Blocked reason: {preview.blocked_reason or 'none'}.",
            f"Readiness: {preview.final_readiness_status}.",
        ]
    )
