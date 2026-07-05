from __future__ import annotations

from .models import LLMDegradedMode, LLMFailureMode, LLMFallbackChain, LLMFallbackDecision, LLMFallbackStep, LLMProviderName, LLMProviderFailureScenario, LLMRoutingFailureSimulation
from .routing_policy import get_fallback_policy


def get_fallback_chain() -> LLMFallbackChain:
    return LLMFallbackChain(tuple(LLMFallbackStep(provider, "metadata-only candidate") for provider in get_fallback_policy().order), False)


def list_failure_scenarios() -> tuple[LLMProviderFailureScenario, ...]:
    return tuple(LLMProviderFailureScenario(mode, mode.value.replace("_", " ")) for mode in (*LLMFailureMode,)) + (LLMProviderFailureScenario(LLMFailureMode.UNKNOWN_FAILURE, "all providers unavailable"),)


def simulate_fallback(scenario: str) -> LLMFallbackDecision:
    normalized = str(scenario or "unknown_failure").strip().lower()
    if normalized == "all_providers_unavailable":
        return LLMFallbackDecision(LLMFailureMode.UNKNOWN_FAILURE, LLMProviderName.MOCK, False, LLMDegradedMode.POLICY_STATUS_ONLY, "All providers are simulated unavailable; return status-only guidance.")
    try:
        failure = LLMFailureMode(normalized)
    except ValueError:
        failure = LLMFailureMode.UNKNOWN_FAILURE
    return LLMFallbackDecision(failure, LLMProviderName.MOCK, False, LLMDegradedMode.MOCK_ONLY, f"Simulated {failure.value}; route stays mock-only and no provider is called.")


def simulate_routing_failure(scenario: str) -> LLMRoutingFailureSimulation:
    decision = simulate_fallback(scenario)
    return LLMRoutingFailureSimulation(decision.scenario, decision)
