from __future__ import annotations

from dataclasses import asdict, dataclass


VOICE_LIFECYCLE_STATES = (
    "disabled",
    "idle",
    "wake_preview",
    "listening_preview",
    "transcript_preview",
    "transcript_blocked",
    "confirmation_required",
    "routed_to_agent_preview",
    "response_preview",
    "stopped_safely",
)


@dataclass(frozen=True)
class TranscriptSafetyResult:
    classification: str
    redacted: bool
    safe_transcript: str
    flags: tuple[str, ...]
    blocked_reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_transcript_safety

        return format_transcript_safety(self)


@dataclass(frozen=True)
class VoiceProviderPolicyEntry:
    name: str
    function: str
    status: str
    sdk_imported: bool
    api_called: bool
    local_engine_invoked: bool


@dataclass(frozen=True)
class VoiceConfirmationPreview:
    confirmation_received: bool
    action_summary: str
    execution_allowed: bool
    decision: str

    def format(self) -> str:
        from .report import format_confirmation_preview

        return format_confirmation_preview(self)


@dataclass(frozen=True)
class VoiceSessionPreview:
    voice_session_id: str
    current_state: str
    mock_input_transcript: str
    transcript_safety_classification: str
    redaction_status: str
    detected_intent_summary: str
    selected_route_preview: str
    confirmation_requirement: str
    execution_gate_decision_summary: str
    response_mode: str
    blocked_reason: str
    final_readiness_status: str
    no_microphone_access_statement: str
    no_audio_playback_statement: str
    no_live_asr_tts_statement: str
    no_live_llm_call_statement: str
    no_tool_execution_statement: str
    no_new_write_path_statement: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_voice_session_preview

        return format_voice_session_preview(self)


@dataclass(frozen=True)
class VoiceAssistantStatus:
    status: str
    mode: str
    lifecycle_state: str
    microphone_access_enabled: bool
    audio_playback_enabled: bool
    live_asr_tts_enabled: bool
    live_llm_calls_enabled: bool
    provider_sdks_enabled: bool
    tool_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    arbitrary_file_writes_enabled: bool
    cloud_voice_enabled: bool
    transcript_safety_status: str
    confirmation_policy: str
    execution_gate_integration: str
    readiness: str
    next_phase: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
