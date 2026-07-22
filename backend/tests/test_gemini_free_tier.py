"""Executable spec for Gemini free-tier limits (Phase 84).

The router already rotated multiple Gemini API keys, but the rate limiter capped
gemini at a flat 4 RPM / 18 requests-per-DAY -- roughly 80x below Google's real
free tier -- so the generous free quota the user was paying attention to was
being thrown away by an over-conservative soft limit, not by Google.

The fix gives gemini per-model limits (like groq already had), applied per key:

  1. Each model gets its real free-tier RPD (2.5-flash 250, 2.0-flash 1500, ...),
     not a flat 18.
  2. The router's per-key ``model[keyN]`` slot suffix is stripped for the lookup,
     and each key is tracked independently -- so N keys give ~N x the daily
     quota. Exhausting one key does not block the next.
  3. Every value stays env-overridable (GEMINI_SOFT_RPM / GEMINI_SOFT_RPD).
"""

from __future__ import annotations

import pytest

from eva.llm.rate_limiter import (
    GEMINI_MODEL_LIMITS,
    LLMRateLimiter,
    provider_limits,
)


class TestPerModelLimits:
    def test_flash_models_are_generous_not_18(self) -> None:
        rpm, rpd = provider_limits("gemini", "gemini-2.5-flash")
        assert (rpm, rpd) == (10, 250)
        assert provider_limits("gemini", "gemini-2.0-flash") == (15, 1500)

    def test_pro_is_tighter_than_flash(self) -> None:
        _, flash_rpd = provider_limits("gemini", "gemini-2.5-flash")
        _, pro_rpd = provider_limits("gemini", "gemini-2.5-pro")
        assert pro_rpd < flash_rpd

    def test_the_old_flat_18_per_day_cap_is_gone(self) -> None:
        for model in GEMINI_MODEL_LIMITS:
            _, rpd = provider_limits("gemini", model)
            assert rpd >= 100, f"{model} is still throttled near the old 18/day cap ({rpd})"

    def test_unknown_gemini_model_gets_a_sane_default_not_18(self) -> None:
        _, rpd = provider_limits("gemini", "gemini-9.9-experimental")
        assert rpd >= 100


class TestPerKeySlotSuffix:
    def test_key_slot_suffix_resolves_to_the_base_model_limit(self) -> None:
        base = provider_limits("gemini", "gemini-2.0-flash")
        for slot in ("gemini-2.0-flash[key0]", "gemini-2.0-flash[key1]", "gemini-2.0-flash[key9]"):
            assert provider_limits("gemini", slot) == base, f"{slot} did not resolve to the base model limit"


class TestEnvOverrideStillWins:
    def test_env_override(self, monkeypatch) -> None:
        monkeypatch.setenv("GEMINI_SOFT_RPD", "4242")
        monkeypatch.setenv("GEMINI_SOFT_RPM", "99")
        assert provider_limits("gemini", "gemini-2.5-flash") == (99, 4242)


class TestKeysAreTrackedIndependently:
    def test_exhausting_one_key_does_not_block_another(self, tmp_path, monkeypatch) -> None:
        """The property that makes N keys worth N x the quota: each key's slot has
        its own daily counter, so key0 hitting its cap leaves key1 free."""
        monkeypatch.setenv("GEMINI_SOFT_RPD", "3")  # tiny cap for a fast test
        limiter = LLMRateLimiter(path=tmp_path / "usage.json")

        # Burn key0's daily budget.
        for _ in range(3):
            ok, _reason = limiter.can_call("gemini", "gemini-2.5-flash[key0]")
            assert ok
            limiter.record_success("gemini", "gemini-2.5-flash[key0]")

        # key0 is now exhausted...
        ok0, reason0 = limiter.can_call("gemini", "gemini-2.5-flash[key0]")
        assert ok0 is False and reason0 == "soft_limit_exhausted:rpd"

        # ...but key1 is untouched.
        ok1, _r = limiter.can_call("gemini", "gemini-2.5-flash[key1]")
        assert ok1 is True, "exhausting key0 wrongly blocked key1 -- N keys would not multiply the quota"
