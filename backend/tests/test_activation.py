"""Executable spec for capability activation profiles (Phase 37a).

The activation layer is the safe "turn Eva on" switch. These tests lock the
invariants that keep it from disturbing the security model:

  * the ``safe`` (default) profile is a pure no-op — the property that keeps the
    whole verifier/test suite byte-identical to before activation existed;
  * the ``daily`` profile enables ONLY the three side-effect-free "mind" flags
    and never any hands/external flag;
  * an explicit operator setting is never overwritten; and
  * ``current_activation_status`` reads live env state truthfully.
"""

from __future__ import annotations

from backend.eva.runtime.activation import (
    NEVER_AUTO_ENABLE,
    activate_profile,
    current_activation_status,
    profile_flags,
)

_DAILY_MIND_FLAGS = {
    "EVA_TRACING_ENABLED",
    "EVA_V2_VECTOR_MEMORY_ENABLED",
    "EVA_NATIVE_FUNCTION_CALLING",
    "EVA_USER_MODEL_ENABLED",
}


def test_safe_profile_is_a_pure_noop():
    env: dict[str, str] = {}
    result = activate_profile("safe", environ=env)
    assert env == {}, "the safe profile must not mutate the environment"
    assert result["applied"] == {}


def test_daily_profile_enables_only_mind_flags():
    env: dict[str, str] = {}
    result = activate_profile("daily", environ=env)
    assert set(result["applied"]) == _DAILY_MIND_FLAGS
    assert set(env) == _DAILY_MIND_FLAGS
    assert all(flag not in env for flag in NEVER_AUTO_ENABLE)


def test_no_profile_can_auto_enable_hands_or_external():
    for name in ("safe", "daily"):
        assert not (set(profile_flags(name)) & NEVER_AUTO_ENABLE), name


def test_explicit_setting_is_never_overwritten():
    env = {"EVA_TRACING_ENABLED": "0"}
    result = activate_profile("daily", environ=env)
    assert env["EVA_TRACING_ENABLED"] == "0", "an explicit operator value must win"
    assert result["already_set"].get("EVA_TRACING_ENABLED") == "0"
    # the other two mind flags were still filled in
    assert env.get("EVA_V2_VECTOR_MEMORY_ENABLED") == "1"


def test_unknown_profile_is_a_noop():
    env: dict[str, str] = {}
    activate_profile("does-not-exist", environ=env)
    assert env == {}


def test_profile_read_from_env_variable():
    env = {"EVA_PROFILE": "daily"}
    activate_profile(environ=env)
    assert env.get("EVA_NATIVE_FUNCTION_CALLING") == "1"


def test_status_reflects_env_state():
    env = {"EVA_PROFILE": "daily", "EVA_TRACING_ENABLED": "1"}
    status = current_activation_status(environ=env)
    assert status["profile"] == "daily"
    assert status["mind"]["tracing"] is True
    assert status["mind"]["vector_memory"] is False
    # hands/external default off
    assert status["hands_external"]["real_input"] is False
