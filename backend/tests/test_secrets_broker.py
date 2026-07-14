"""Tests for the Phase 40c secrets broker.

The broker is the single mediation point between the real process environment
and anything that reaches a tool, the model, or a trace: discovery returns
names only, resolution gates on a secret-looking name, and scrubbing removes
both known-shaped secrets (pattern) and any live secret value verbatim
(exact-match) before text is safe to send to the model. All tests use plain
dict environs -- the real process environment is never touched.
"""

from __future__ import annotations

from backend.eva.privacy import secrets_broker as broker

OPENAI_KEY = "sk-abc1234567890xyzsecretlong"
GEMINI_KEY = "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ1234"

ENV = {
    "OPENAI_API_KEY": OPENAI_KEY,
    "GEMINI_API_KEY": GEMINI_KEY,
    "HOME": "/home/x",
}


def test_list_secret_names_returns_only_secret_names_sorted_no_values():
    names = broker.list_secret_names(ENV)

    assert names == sorted(["OPENAI_API_KEY", "GEMINI_API_KEY"])
    assert "HOME" not in names
    for name in names:
        assert OPENAI_KEY not in name
        assert GEMINI_KEY not in name


def test_resolve_gates_on_secret_looking_name():
    assert broker.resolve("OPENAI_API_KEY", ENV) == OPENAI_KEY
    assert broker.resolve("HOME", ENV) is None
    assert broker.resolve("does_not_exist_token", ENV) is None


def test_has_secret():
    assert broker.has_secret("OPENAI_API_KEY", ENV) is True
    assert broker.has_secret("HOME", ENV) is False
    assert broker.has_secret("GEMINI_API_KEY", {}) is False


def test_scrub_for_model_removes_both_values_and_adds_placeholder():
    text = f"token is {OPENAI_KEY} and {GEMINI_KEY}"

    scrubbed = broker.scrub_for_model(text, ENV)

    assert OPENAI_KEY not in scrubbed
    assert GEMINI_KEY not in scrubbed
    assert "REDACTED" in scrubbed


def test_contains_secret_leak_true_on_raw_false_on_scrubbed():
    raw = f"leak: {OPENAI_KEY}"

    assert broker.contains_secret_leak(raw, ENV) is True

    scrubbed = broker.scrub_for_model(raw, ENV)
    assert broker.contains_secret_leak(scrubbed, ENV) is False


def test_assert_no_secret_leak_true_after_scrubbing_pipeline():
    raw = f"my key is {OPENAI_KEY}, please keep it safe"

    assert broker.assert_no_secret_leak(raw, ENV) is True


def test_scrub_for_model_is_fail_safe_on_odd_input():
    assert isinstance(broker.scrub_for_model(None, ENV), str)
    assert isinstance(broker.scrub_for_model(12345, ENV), str)
    assert isinstance(broker.scrub_for_model("", ENV), str)


def test_short_secret_value_does_not_corrupt_unrelated_text():
    env = {"SHORT_TOKEN": "abc"}
    text = "abc is a common word fragment that should survive scrubbing"

    scrubbed = broker.scrub_for_model(text, env)

    assert scrubbed == text
