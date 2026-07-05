from __future__ import annotations

from .models import VoiceProviderPolicyEntry
from .voice_policy import boundary_lines


def provider_policy_entries() -> tuple[VoiceProviderPolicyEntry, ...]:
    return tuple(
        VoiceProviderPolicyEntry(
            name=name,
            function=function,
            status="locked candidate only",
            sdk_imported=False,
            api_called=False,
            local_engine_invoked=False,
        )
        for name, function in (
            ("Whisper", "future ASR candidate"),
            ("Piper", "future TTS candidate"),
            ("Coqui", "future TTS candidate"),
            ("ElevenLabs", "future hosted TTS candidate"),
            ("OpenAI voice", "future hosted voice candidate"),
            ("browser speech", "future browser voice candidate"),
            ("OS speech", "future operating-system voice candidate"),
        )
    )


def provider_policy_text() -> str:
    lines = [
        "ASR/TTS provider policy",
        *boundary_lines(),
        "All providers are locked candidates only.",
        "Future provider selection requires explicit configuration and safety review.",
        "No provider SDK is imported and no provider API is called.",
        "No local ASR/TTS engine is invoked.",
    ]
    lines.extend(f"- {entry.name}: {entry.function}; {entry.status}." for entry in provider_policy_entries())
    return "\n".join(lines)
