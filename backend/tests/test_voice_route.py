"""The voice loop, wired end to end (Phase 61 / the "49c" gap).

``voice/listener.listen_once`` always produced a transcript, but nothing in the
app invoked it. ``POST /api/chat/voice`` now captures one utterance and routes
its transcript through the SAME pipeline as typed text. These tests inject a
canned transcript (no microphone, no model, no network) and pin the invariants:

  * voice off / no wake => no chat turn, the reason is surfaced;
  * a heard message yields the SAME reply as the identical typed message
    (speech re-enters through chat(); it earns no privilege);
  * the status endpoint opens no device and reports "off" by default.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.eva.main import app
from backend.eva.voice.listener import ListenResult

HEADERS = {"X-Eva-Client": "1"}
# Resolves in the deterministic pre-LLM stages, so no provider/network is needed.
DETERMINISTIC = "eva capability truth"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _patch_listen(monkeypatch, result: ListenResult):
    monkeypatch.setattr("backend.eva.api.routes.listen_once", lambda: result)


def test_voice_disabled_yields_no_chat_turn(client, monkeypatch):
    # listen_once refuses when voice input is off — no device is opened.
    _patch_listen(monkeypatch, ListenResult(reason="voice_input_disabled"))
    resp = client.post("/api/chat/voice", json={}, headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["reason"] == "voice_input_disabled"
    assert body["transcript"] == "" and body["reply"] == ""
    assert body["woke"] is False and body["source"] == "voice"


def test_wake_timeout_yields_no_chat_turn(client, monkeypatch):
    _patch_listen(monkeypatch, ListenResult(reason="wake_timeout"))
    body = client.post("/api/chat/voice", json={}, headers=HEADERS).json()
    assert body["reason"] == "wake_timeout"
    assert body["reply"] == "" and body["woke"] is False


def test_heard_message_matches_the_same_typed_message(client, monkeypatch):
    """The security property, made concrete: a spoken message is handled exactly
    like the same message typed — same pipeline, same gate."""
    typed = client.post("/api/chat", json={"message": DETERMINISTIC}, headers=HEADERS).json()

    _patch_listen(monkeypatch, ListenResult(text=DETERMINISTIC, woke=True, wake_word="hey_jarvis", reason="ok"))
    spoken = client.post("/api/chat/voice", json={}, headers=HEADERS).json()

    assert spoken["transcript"] == DETERMINISTIC
    assert spoken["woke"] is True and spoken["wake_word"] == "hey_jarvis"
    # The reply is byte-identical to typing it — the transcript went through chat().
    assert spoken["reply"] == typed["reply"]
    # Source records that this arrived by voice but names the same underlying route.
    assert spoken["source"] == f"voice+{typed['source']}"


def test_listen_status_opens_no_device_and_is_off_by_default(client):
    body = client.get("/api/voice/listen/status", headers=HEADERS).json()
    # Reports the stack without opening a device; voice input is opt-in.
    assert body.get("enabled") is False
    assert body.get("microphone_available") is False
    assert "bounds" in body and "wake_timeout_seconds" in body["bounds"]
