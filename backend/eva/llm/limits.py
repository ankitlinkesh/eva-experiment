from __future__ import annotations

from .models import LLMCostBudget, LLMRateLimitPolicy, LLMRunawayProtectionPolicy, LLMTokenBudget


def get_token_budget() -> LLMTokenBudget:
    return LLMTokenBudget(4000, 1000)


def get_cost_budget() -> LLMCostBudget:
    return LLMCostBudget(0.0, "Live calls are locked, so no cost can be incurred in Phase 15A.")


def get_rate_limit_policy() -> LLMRateLimitPolicy:
    return LLMRateLimitPolicy(4, "Simulate a degraded mock-only response; never retry a live provider in Phase 15B.")


def get_runaway_protection_policy() -> LLMRunawayProtectionPolicy:
    return LLMRunawayProtectionPolicy(8, "Stop with a status-only explanation when the preview step limit is reached.")
