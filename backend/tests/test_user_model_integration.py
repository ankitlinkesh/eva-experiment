"""MemoryStore <-> durable user model integration (Phase 43).

Proves the wiring: user turns teach the model, chat recall carries the durable
block, and everything is a byte-identical no-op when the feature flag is off.
"""

from __future__ import annotations

import pytest

from eva.memory.store import MemoryStore


def _durable_blocks(history):
    # The durable user-model block is identified by its marker text so it is
    # distinguished from the separate semantic-recall block the vector-memory
    # path may also inject.
    return [m for m in history if m.get("role") == "system" and "durable memory" in (m.get("content") or "")]


def test_flag_off_is_a_no_op(tmp_path, monkeypatch):
    monkeypatch.delenv("EVA_USER_MODEL_ENABLED", raising=False)
    ms = MemoryStore(tmp_path / "off.db")
    ms.add_message("s1", "user", "My name is Ankit and I live in Delhi")
    assert ms._user_model() is None
    history = ms.history_with_recall("s1", "anything")
    assert _durable_blocks(history) == []


def test_flag_on_learns_and_injects_durable_block(tmp_path, monkeypatch):
    monkeypatch.setenv("EVA_USER_MODEL_ENABLED", "1")
    ms = MemoryStore(tmp_path / "on.db")
    ms.add_message("s1", "user", "My name is Ankit and I live in Delhi")
    ms.add_message("s1", "user", "I am allergic to peanuts")
    history = ms.history_with_recall("s1", "what should I eat")
    blocks = _durable_blocks(history)
    assert blocks, "a durable user-model block must be prepended"
    content = blocks[0]["content"]
    assert "Ankit" in content
    assert "Delhi" in content


def test_durable_model_is_cross_session(tmp_path, monkeypatch):
    monkeypatch.setenv("EVA_USER_MODEL_ENABLED", "1")
    ms = MemoryStore(tmp_path / "cross.db")
    ms.add_message("session-a", "user", "I am allergic to peanuts")
    # A brand-new session still sees the durable fact — the whole point of a
    # compounding user model vs. per-session recent history.
    history = ms.history_with_recall("session-b", "what foods are dangerous for me")
    blocks = _durable_blocks(history)
    assert blocks and "peanuts" in blocks[0]["content"]


def test_assistant_turns_do_not_teach(tmp_path, monkeypatch):
    monkeypatch.setenv("EVA_USER_MODEL_ENABLED", "1")
    ms = MemoryStore(tmp_path / "asst.db")
    ms.add_message("s1", "assistant", "My name is Eva and I live in the cloud")
    assert ms._user_model().summary()["belief_count"] == 0


def test_consolidate_scans_recent_user_turns(tmp_path, monkeypatch):
    monkeypatch.setenv("EVA_USER_MODEL_ENABLED", "1")
    ms = MemoryStore(tmp_path / "consolidate.db")
    ms.add_message("s1", "user", "My name is Ankit")
    ms.add_message("s1", "user", "I work at Acme Corp")
    result = ms._user_model().consolidate(ms, session_id="s1")
    assert result["scanned"] >= 2
    assert result["learned"] >= 1
