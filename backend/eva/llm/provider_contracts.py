from __future__ import annotations

from .models import LLMProviderCapability, LLMProviderContract, LLMProviderName, LLMProviderStatus


def list_provider_contracts() -> tuple[LLMProviderContract, ...]:
    blocked = LLMProviderCapability(supports_live_calls_now=False)
    return (
        LLMProviderContract(LLMProviderName.GEMINI, LLMProviderStatus.CONFIGURED_METADATA_ONLY, blocked, "Metadata only; Phase 15A makes no provider call."),
        LLMProviderContract(LLMProviderName.GROQ, LLMProviderStatus.CONFIGURED_METADATA_ONLY, blocked, "Metadata only; Phase 15A makes no provider call."),
        LLMProviderContract(LLMProviderName.OPENROUTER, LLMProviderStatus.CONFIGURED_METADATA_ONLY, blocked, "Metadata only; Phase 15A makes no provider call."),
        LLMProviderContract(LLMProviderName.CLAUDE, LLMProviderStatus.CONFIGURED_METADATA_ONLY, blocked, "Metadata only; Phase 15A makes no provider call."),
        LLMProviderContract(LLMProviderName.OLLAMA, LLMProviderStatus.BLOCKED_LIVE_CALLS, blocked, "Local provider metadata only; live calls stay locked in this phase."),
        LLMProviderContract(LLMProviderName.MOCK, LLMProviderStatus.AVAILABLE_MOCK_ONLY, LLMProviderCapability(), "Deterministic dry-run provider for contract validation only."),
    )
