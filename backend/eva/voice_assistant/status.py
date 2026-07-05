from __future__ import annotations

from .models import VoiceAssistantStatus


def get_voice_assistant_status() -> VoiceAssistantStatus:
    return VoiceAssistantStatus(
        status="available",
        mode="local/mock preview only",
        lifecycle_state="disabled",
        microphone_access_enabled=False,
        audio_playback_enabled=False,
        live_asr_tts_enabled=False,
        live_llm_calls_enabled=False,
        provider_sdks_enabled=False,
        tool_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        arbitrary_file_writes_enabled=False,
        cloud_voice_enabled=False,
        transcript_safety_status="active for bundled mock transcripts",
        confirmation_policy="preview only; confirmation alone never executes",
        execution_gate_integration="local policy preview only",
        readiness="ready for future reviewed integration; live voice locked",
        next_phase="Phase 23 AI OS / Control Center Upgrade",
    )
