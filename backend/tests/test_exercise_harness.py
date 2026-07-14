"""Executable spec for the dogfood exercise/friction harness (Phase 37b).

The harness drives realistic scenarios through the real gate under tracing and
distils a friction report. These tests lock:

  * the offline suite runs and produces sensible aggregate friction metrics;
  * a gated scenario is recorded as a gate-hold with zero tool executions;
  * a scenario whose drive raises is captured as an error, not a crash; and
  * the harness restores tracing state (env flag + trace-store root) afterward,
    so an exercise run never pollutes the real trace store or leaks activation.
"""

from __future__ import annotations

import os

import backend.eva.observability.local_trace_store as local_trace_store
from backend.eva.evals.exercise import (
    ExerciseScenario,
    offline_scenarios,
    run_exercise,
    run_offline_exercise,
)
from backend.eva.evals.models import EvalContext


def test_offline_scenarios_present():
    assert len(offline_scenarios()) >= 3


def test_offline_exercise_produces_friction_metrics():
    report = run_offline_exercise()
    assert report.scenarios == len(offline_scenarios())
    assert report.total_tool_calls >= 1
    assert report.total_gate_holds >= 1
    assert "gate-holds" in report.summary_text()


def test_gated_scenario_is_held_not_executed():
    report = run_offline_exercise()
    observe = next(t for t in report.traces if t.scenario_id == "observe_requires_confirmation")
    assert observe.gate_holds >= 1
    assert observe.tool_calls == 0, "an override-class tool must never execute during exercise"


def test_broken_scenario_is_captured_not_crashed():
    def _boom(ctx: EvalContext) -> None:
        raise RuntimeError("scenario blew up")

    scenario = ExerciseScenario(id="boom", description="raises on purpose", category="test", drive=_boom)
    report = run_exercise([scenario])
    assert report.scenarios == 1
    assert report.traces[0].error is not None
    assert "RuntimeError" in report.traces[0].error


def test_exercise_restores_tracing_state(monkeypatch):
    # Ensure the flag starts unset and the root is captured, then confirm both
    # are restored to their pre-run values after the harness runs.
    monkeypatch.delenv("EVA_TRACING_ENABLED", raising=False)
    original_root = local_trace_store.DEFAULT_TRACE_ROOT

    run_offline_exercise()

    assert "EVA_TRACING_ENABLED" not in os.environ, "the tracing flag must not leak past the run"
    assert local_trace_store.DEFAULT_TRACE_ROOT == original_root, "the trace-store root must be restored"
