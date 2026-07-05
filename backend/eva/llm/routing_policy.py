from __future__ import annotations

from .models import LLMFallbackPolicy, LLMProviderName, LLMRetryPolicy, LLMRoutingPolicy, LLMTimeoutPolicy, LLMFailureMode


def get_routing_policy() -> LLMRoutingPolicy:
    return LLMRoutingPolicy("phase15a_mock_only", False, True, LLMProviderName.MOCK, "Routing decisions are previews only. Live provider calls are locked.")


def get_fallback_policy() -> LLMFallbackPolicy:
    return LLMFallbackPolicy((LLMProviderName.GEMINI, LLMProviderName.GROQ, LLMProviderName.OPENROUTER, LLMProviderName.CLAUDE, LLMProviderName.OLLAMA, LLMProviderName.MOCK), "Degrade to mock/status-only; never call a live provider in Phase 15A.")


def get_timeout_policy() -> LLMTimeoutPolicy:
    return LLMTimeoutPolicy(30)


def get_retry_policy() -> LLMRetryPolicy:
    return LLMRetryPolicy(2, (LLMFailureMode.TIMEOUT, LLMFailureMode.RATE_LIMITED))
