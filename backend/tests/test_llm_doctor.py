"""LLM provider diagnostics (Phase 48).

The point of the doctor is to make provider rot *visible*, so these tests pin
the two things that matter: it reports the truth about configuration, and it
never touches the network.
"""

from __future__ import annotations

import pytest

from eva.llm.doctor import (
    PROVIDER_KEY_ENV,
    configuration_report,
    format_configuration_report,
    gemini_key_names,
)


def test_report_is_offline():
    report = configuration_report(environ={})
    assert report["network_used"] is False


def test_report_makes_no_network_call(monkeypatch):
    """Hard guarantee: if the doctor ever reached the network, CI would be
    flaky and slow. Poison every socket and prove it still works."""
    import socket

    def _boom(*args, **kwargs):
        raise AssertionError("configuration_report must never open a socket")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    report = configuration_report(environ={"NVIDIA_NIM_API_KEY": "x"})
    assert report["providers"]["nvidia_nim"]["configured"] is True


def test_detects_configured_and_unconfigured():
    env = {"NVIDIA_NIM_API_KEY": "k", "EVA_CLOUD_PROVIDER_ORDER": "nvidia_nim,groq"}
    report = configuration_report(environ=env)
    assert report["providers"]["nvidia_nim"]["configured"] is True
    assert report["providers"]["groq"]["configured"] is False


def test_flags_a_keyless_provider_in_the_order():
    """The actionable finding: a provider in the order with no key burns a
    failed attempt on every single call."""
    env = {"NVIDIA_NIM_API_KEY": "k", "EVA_CLOUD_PROVIDER_ORDER": "nvidia_nim,groq,clod"}
    report = configuration_report(environ=env)
    assert set(report["unconfigured_in_order"]) == {"groq", "clod"}
    assert any("wastes an attempt" in w for w in report["warnings"])


def test_no_warning_when_order_is_clean():
    env = {"NVIDIA_NIM_API_KEY": "k", "EVA_CLOUD_PROVIDER_ORDER": "nvidia_nim,ollama"}
    report = configuration_report(environ=env)
    assert report["unconfigured_in_order"] == []


def test_warns_when_nothing_is_configured():
    report = configuration_report(environ={"EVA_CLOUD_PROVIDER_ORDER": "gemini,openrouter"})
    assert any("no working cloud LLM" in w for w in report["warnings"])


def test_counts_the_gemini_rotation_pool():
    env = {"GEMINI_API_KEY": "a", "GEMINI_API_KEY_2": "b", "GEMINI_API_KEY_4": "d", "GEMINI_API_KEY_3": "  "}
    names = gemini_key_names(environ=env)
    assert names == ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_4"]
    report = configuration_report(environ=env)
    assert report["providers"]["gemini"]["rotation_key_count"] == 3
    assert report["providers"]["gemini"]["configured"] is True


def test_gemini_unconfigured_without_any_key():
    report = configuration_report(environ={})
    assert report["providers"]["gemini"]["configured"] is False


def test_report_never_contains_a_secret_value():
    secret = "super-secret-key-value-123456"
    env = {"NVIDIA_NIM_API_KEY": secret, "GEMINI_API_KEY": secret, "OPENROUTER_API_KEY": secret}
    text = format_configuration_report(configuration_report(environ=env))
    assert secret not in text, "a diagnostic must never print a key value"


def test_formatting_is_readable():
    text = format_configuration_report(configuration_report(environ={"NVIDIA_NIM_API_KEY": "k"}))
    assert "no network calls made" in text
    assert "nvidia_nim" in text


def test_every_known_provider_is_covered():
    for provider in ("nvidia_nim", "gemini", "openrouter", "groq", "clod", "ollama"):
        assert provider in PROVIDER_KEY_ENV


def test_report_is_fail_safe_on_garbage():
    report = configuration_report(environ={"EVA_CLOUD_PROVIDER_ORDER": ",,,"})
    assert report["provider_order"] == []
