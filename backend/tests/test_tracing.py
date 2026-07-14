"""Executable spec for the flight-recorder trace context (Phase 36a).

Covers the invariants the observability core promises:

  * default-off and byte-identical when off -- with ``EVA_TRACING_ENABLED``
    unset, nothing is written to disk and every helper is a no-op;
  * ambient trace id propagation through the tool gate (``ToolRegistry.run``)
    without any call-site plumbing;
  * a gated (override/confirm) tool call only ever produces a ``permission``
    event, never a ``tool_call`` event, since the handler never runs;
  * the contextvar is always cleared once ``task_trace`` exits, even though
    the manager is a sync contextmanager wrapped around async work; and
  * tracing failures never propagate into the caller.

Every test redirects ``LocalTraceStore``'s default root at
``backend.eva.observability.local_trace_store.DEFAULT_TRACE_ROOT`` to a
throwaway ``tmp_path`` so no test ever touches the real trace directory.
"""

from __future__ import annotations

import pytest


def _redirect_trace_root(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr("backend.eva.observability.local_trace_store.DEFAULT_TRACE_ROOT", tmp_path)


def test_tracing_off_by_default_writes_nothing(tmp_path, monkeypatch):
    _redirect_trace_root(monkeypatch, tmp_path)
    monkeypatch.delenv("EVA_TRACING_ENABLED", raising=False)

    from backend.eva.observability.context import get_current_trace_id, task_trace, tracing_enabled

    assert tracing_enabled() is False

    with task_trace("req-off", "goal-off") as trace_id:
        assert trace_id is None
        assert get_current_trace_id() is None
    assert get_current_trace_id() is None

    from backend.eva.tools.registry import ToolRegistry

    result = ToolRegistry().run("workspace_status")
    assert isinstance(result, dict)
    assert list(tmp_path.glob("*.jsonl")) == [], "no trace files may be written while tracing is off"


def test_tracing_on_records_allowed_tool_call(tmp_path, monkeypatch):
    _redirect_trace_root(monkeypatch, tmp_path)
    monkeypatch.setenv("EVA_TRACING_ENABLED", "1")

    from backend.eva.observability import traces
    from backend.eva.observability.context import get_current_trace_id, task_trace
    from backend.eva.tools.registry import ToolRegistry

    with task_trace("req-on", "goal-on") as trace_id:
        assert trace_id, "an enabled trace must yield a truthy trace id"
        assert get_current_trace_id() == trace_id

        result = ToolRegistry().run("workspace_status")
        assert isinstance(result, dict)

    trace = traces.read_trace(trace_id)
    assert trace["found"] is True
    events = trace["events"]

    permission_events = [event for event in events if event.get("type") == "permission"]
    assert any(
        event["payload"].get("tool_name") == "workspace_status" and event["payload"].get("decision") == "allow"
        for event in permission_events
    ), f"missing allow permission event for workspace_status: {permission_events}"

    tool_call_events = [event for event in events if event.get("type") == "tool_call"]
    assert any(event["payload"].get("tool_name") == "workspace_status" for event in tool_call_events), (
        f"missing tool_call event for workspace_status: {tool_call_events}"
    )


def test_gated_tool_call_records_override_permission_but_no_tool_call(tmp_path, monkeypatch):
    _redirect_trace_root(monkeypatch, tmp_path)
    monkeypatch.setenv("EVA_TRACING_ENABLED", "1")

    from backend.eva.observability import traces
    from backend.eva.observability.context import task_trace
    from backend.eva.tools.registry import ToolRegistry

    with task_trace("req-gated", "goal-gated") as trace_id:
        assert trace_id
        result = ToolRegistry().run("screen.observe", reason="unit-test-observation")
        assert result.get("requires_confirmation") is True, f"screen.observe should be gated: {result}"

    trace = traces.read_trace(trace_id)
    events = trace["events"]

    permission_events = [event for event in events if event.get("type") == "permission"]
    assert any(
        event["payload"].get("tool_name") == "screen.observe" and event["payload"].get("decision") == "override"
        for event in permission_events
    ), f"missing override permission event for screen.observe: {permission_events}"

    tool_call_events = [
        event for event in events if event.get("type") == "tool_call" and event["payload"].get("tool_name") == "screen.observe"
    ]
    assert tool_call_events == [], "a gated call must not reach _invoke, so no tool_call event may exist"


def test_context_var_cleared_after_trace_exits(tmp_path, monkeypatch):
    _redirect_trace_root(monkeypatch, tmp_path)
    monkeypatch.setenv("EVA_TRACING_ENABLED", "1")

    from backend.eva.observability.context import get_current_trace_id, task_trace

    with task_trace("req-isolation", "goal-isolation") as trace_id:
        assert trace_id
        assert get_current_trace_id() == trace_id
    assert get_current_trace_id() is None, "trace id must not leak past the task_trace scope"


def test_tracing_failure_does_not_propagate_to_caller(tmp_path, monkeypatch):
    _redirect_trace_root(monkeypatch, tmp_path)
    monkeypatch.setenv("EVA_TRACING_ENABLED", "1")
    monkeypatch.setattr(
        "backend.eva.observability.traces.log_tool_call",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    from backend.eva.observability.context import task_trace
    from backend.eva.tools.registry import ToolRegistry

    with task_trace("req-failsafe", "goal-failsafe"):
        result = ToolRegistry().run("workspace_status")

    assert isinstance(result, dict)
    assert result.get("ok") is True, f"a broken trace sink must not affect the tool's real result: {result}"
