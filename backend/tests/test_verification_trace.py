"""Executable spec for the verification trace event (Phase 38).

``ToolRegistry._invoke`` independently checks a tool's declared post-condition
and, only when tracing is on, records the outcome as a ``verification`` event
via ``trace_verification`` (backend/eva/observability/context.py). Covers:

  * with tracing on, an allow-class call (``workspace_status``) produces a
    ``verification`` event whose payload names the tool and its provenance; and
  * with tracing off (the default), no trace file is written at all, so the
    verification check stays on the same byte-identical hot path as the rest
    of the flight recorder.

Every test redirects ``LocalTraceStore``'s default root to a throwaway
``tmp_path``, matching the convention in test_tracing.py.
"""

from __future__ import annotations

import pytest


def _redirect_trace_root(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr("backend.eva.observability.local_trace_store.DEFAULT_TRACE_ROOT", tmp_path)


def test_verification_event_recorded_when_tracing_is_on(tmp_path, monkeypatch):
    _redirect_trace_root(monkeypatch, tmp_path)
    monkeypatch.setenv("EVA_TRACING_ENABLED", "1")

    from backend.eva.observability import traces
    from backend.eva.observability.context import task_trace
    from backend.eva.tools.registry import ToolRegistry

    with task_trace("req-verify", "goal-verify") as trace_id:
        assert trace_id
        result = ToolRegistry().run("workspace_status")
        assert isinstance(result, dict)

    trace = traces.read_trace(trace_id)
    assert trace["found"] is True
    events = trace["events"]

    verification_events = [event for event in events if event.get("type") == "verification"]
    assert verification_events, f"missing verification event: {events}"
    payload = verification_events[0]["payload"]
    assert payload.get("tool_name") == "workspace_status"
    assert payload.get("provenance") == "self_reported"


def test_no_verification_event_or_trace_file_when_tracing_is_off(tmp_path, monkeypatch):
    _redirect_trace_root(monkeypatch, tmp_path)
    monkeypatch.delenv("EVA_TRACING_ENABLED", raising=False)

    from backend.eva.observability.context import task_trace
    from backend.eva.tools.registry import ToolRegistry

    with task_trace("req-verify-off", "goal-verify-off") as trace_id:
        assert trace_id is None
        result = ToolRegistry().run("workspace_status")
        assert isinstance(result, dict)

    assert list(tmp_path.glob("*.jsonl")) == [], "tracing-off must stay a byte-identical no-op hot path"
