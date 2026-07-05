from __future__ import annotations

from .models import LLMDegradedMode, LLMDegradedModeDecision, LLMDegradedModePolicy


def get_degraded_mode_policy() -> LLMDegradedModePolicy:
    return LLMDegradedModePolicy(LLMDegradedMode.MOCK_ONLY, "Use mock/status-only output and never fall through to a live provider.")


def get_degraded_mode_decision() -> LLMDegradedModeDecision:
    policy = get_degraded_mode_policy()
    return LLMDegradedModeDecision(policy.mode, False, policy.behavior)
