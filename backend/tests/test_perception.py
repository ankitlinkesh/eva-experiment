"""Unit tests for the opt-in, metadata-only situational model (Phase 44)."""

from __future__ import annotations

import pytest

from eva.perception import situational_model as sm
from eva.perception.situational_model import (
    Situation,
    capture_situation,
    perception_enabled,
    situational_summary,
)


def test_perception_off_by_default(monkeypatch):
    monkeypatch.delenv("EVA_PERCEPTION_ENABLED", raising=False)
    assert perception_enabled() is False
    monkeypatch.setenv("EVA_PERCEPTION_ENABLED", "0")
    assert perception_enabled() is False
    monkeypatch.setenv("EVA_PERCEPTION_ENABLED", "1")
    assert perception_enabled() is True


def test_auto_summary_is_empty_when_disabled(monkeypatch):
    monkeypatch.delenv("EVA_PERCEPTION_ENABLED", raising=False)
    # No-arg summary honors the opt-in gate → no capture, empty string.
    assert situational_summary() == ""


def test_sensitive_titles_are_redacted():
    assert sm._safe_title("Chase Bank - Login") == "[private window]"
    assert sm._safe_title("WhatsApp") == "[private window]"
    assert sm._safe_title("runner.py - eva-agent") == "runner.py - eva-agent"


def test_explicit_situation_is_always_formatted_and_redacted():
    s = Situation(
        active_app="chrome.exe",
        active_title="MyBank - Sign in",
        open_apps=["chrome.exe", "Code.exe"],
        window_count=2,
        captured_at="t",
    )
    summary = situational_summary(s)
    assert "chrome.exe" in summary
    assert "[private window]" in summary
    assert "MyBank" not in summary  # raw sensitive title never leaks
    assert "no screenshot" in summary.lower()


def test_summary_lists_other_open_apps():
    s = Situation(active_app="Code.exe", active_title="x", open_apps=["Code.exe", "slack.exe", "spotify.exe"], window_count=3, captured_at="t")
    summary = situational_summary(s)
    assert "slack.exe" in summary and "spotify.exe" in summary


def test_unavailable_situation_summarizes_to_empty():
    s = Situation(active_app=None, active_title=None, open_apps=[], window_count=0, captured_at="t", available=False)
    assert situational_summary(s) == ""


def test_capture_is_metadata_only_and_redacts(monkeypatch):
    # Stub the window layer so the test is deterministic and cross-platform.
    class _W:
        def __init__(self, title, process_name):
            self.title = title
            self.process_name = process_name

    monkeypatch.setattr(sm, "capture_situation", capture_situation)  # ensure real fn

    def fake_active():
        return _W("Barclays Bank - Login", "chrome.exe")

    def fake_list():
        return [_W("Barclays Bank - Login", "chrome.exe"), _W("runner.py", "Code.exe"), _W("", "Code.exe")]

    import eva.desktop.windows as win
    monkeypatch.setattr(win, "get_active_window", fake_active)
    monkeypatch.setattr(win, "list_open_windows", fake_list)

    snap = capture_situation()
    assert snap.active_app == "chrome.exe"
    assert snap.active_title == "[private window]"  # sensitive foreground title redacted at capture
    assert snap.privacy_redacted is True
    # open_apps are distinct process names only — never titles.
    assert snap.open_apps == ["chrome.exe", "Code.exe"]
    assert all("Bank" not in app for app in snap.open_apps)


def test_capture_is_fail_safe(monkeypatch):
    import eva.desktop.windows as win

    def boom():
        raise RuntimeError("no windows here")

    monkeypatch.setattr(win, "get_active_window", boom)
    snap = capture_situation()
    assert snap.available is False
    assert snap.active_app is None
