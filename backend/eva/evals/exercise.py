"""Dogfood exercise harness + friction report (Phase 37b).

Phase 36 gave Eva a flight recorder; Phase 37 turns her on and *exercises* her.
This harness drives a set of realistic scenarios through the real tool gate with
tracing enabled, then reads the resulting traces back and distills a **friction
report**: how many tools actually ran, how many calls were held at the gate for
confirmation (the friction an operator feels), how many errored, and which tools
were exercised. That report is the signal Phase 37 exists to produce — it shows,
from real runs rather than assumptions, where Eva strains.

Safety: every offline scenario is deterministic and side-effect-free (gated
tools are only ever *asked* to run — the gate holds them, so they never execute).
The harness enables tracing only for the duration of the run and redirects trace
writes to a throwaway temp directory, restoring both the ``EVA_TRACING_ENABLED``
env var and the trace-store root in a ``finally`` so a run never pollutes the
real trace store or leaks activation state. Nothing here needs a network, a live
LLM, a browser, or any ``EVA_*`` execution flag beyond tracing.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..core.fast_commands import maybe_handle_fast_command
from ..observability.context import task_trace
from .models import EvalContext


@dataclass(frozen=True)
class ExerciseScenario:
    """A realistic sequence of actions to drive through the gate under tracing.

    ``drive`` performs a series of ``ctx.registry.run(...)`` and/or fast-command
    calls; its return value is ignored because the *trace* is the record we score.
    """

    id: str
    description: str
    category: str
    drive: Callable[[EvalContext], None]


@dataclass(frozen=True)
class ScenarioTrace:
    """Friction metrics distilled from one scenario's flight-recorder trace."""

    scenario_id: str
    trace_id: str | None
    tool_calls: int
    gate_holds: int
    allow_calls: int
    errors: int
    tools: tuple[str, ...]
    error: str | None = None


@dataclass
class FrictionReport:
    """Aggregate friction across an exercise run, plus a human summary."""

    traces: list[ScenarioTrace] = field(default_factory=list)

    @property
    def scenarios(self) -> int:
        return len(self.traces)

    @property
    def total_tool_calls(self) -> int:
        return sum(trace.tool_calls for trace in self.traces)

    @property
    def total_gate_holds(self) -> int:
        return sum(trace.gate_holds for trace in self.traces)

    @property
    def total_errors(self) -> int:
        return sum(trace.errors for trace in self.traces)

    @property
    def tools_exercised(self) -> list[str]:
        seen: set[str] = set()
        for trace in self.traces:
            seen.update(trace.tools)
        return sorted(seen)

    def as_dict(self) -> dict[str, object]:
        return {
            "scenarios": self.scenarios,
            "total_tool_calls": self.total_tool_calls,
            "total_gate_holds": self.total_gate_holds,
            "total_errors": self.total_errors,
            "tools_exercised": self.tools_exercised,
            "traces": [
                {
                    "scenario_id": trace.scenario_id,
                    "trace_id": trace.trace_id,
                    "tool_calls": trace.tool_calls,
                    "gate_holds": trace.gate_holds,
                    "allow_calls": trace.allow_calls,
                    "errors": trace.errors,
                    "tools": list(trace.tools),
                    "error": trace.error,
                }
                for trace in self.traces
            ],
        }

    def summary_text(self) -> str:
        lines = [
            f"Eva exercise: {self.scenarios} scenarios, {self.total_tool_calls} tool calls, "
            f"{self.total_gate_holds} confirmation gate-holds, {self.total_errors} errors."
        ]
        for trace in self.traces:
            suffix = f" [drive error: {trace.error}]" if trace.error else ""
            lines.append(
                f"- {trace.scenario_id}: {trace.tool_calls} ran, {trace.gate_holds} held, "
                f"{trace.errors} errored{suffix}"
            )
        lines.append(f"Tools exercised: {', '.join(self.tools_exercised) or '(none)'}")
        return "\n".join(lines)


def _status_sweep(ctx: EvalContext) -> None:
    ctx.registry.run("workspace_status")
    ctx.registry.run("system_status")


def _observe_requires_confirmation(ctx: EvalContext) -> None:
    ctx.registry.run("screen.observe", reason="exercise")


def _mixed_daily_task(ctx: EvalContext) -> None:
    ctx.registry.run("workspace_status")
    ctx.registry.run("screen.observe", reason="exercise")
    maybe_handle_fast_command("traces status", ctx.registry)


def offline_scenarios() -> list[ExerciseScenario]:
    """The deterministic, CI-safe exercise scenarios."""
    return [
        ExerciseScenario(
            id="status_sweep",
            description="Check the workspace and system status (two allow-class reads).",
            category="observation",
            drive=_status_sweep,
        ),
        ExerciseScenario(
            id="observe_requires_confirmation",
            description="Ask to observe the screen (override-class; held at the gate).",
            category="safety",
            drive=_observe_requires_confirmation,
        ),
        ExerciseScenario(
            id="mixed_daily_task",
            description="A mixed daily task: a read, a gated observation, and a routed command.",
            category="mixed",
            drive=_mixed_daily_task,
        ),
    ]


def _metrics_from_events(scenario_id: str, trace_id: str | None, events: list[dict], error: str | None) -> ScenarioTrace:
    tool_calls = 0
    gate_holds = 0
    allow_calls = 0
    errors = 0
    tools: list[str] = []
    for event in events:
        etype = event.get("type")
        payload = event.get("payload") or {}
        if etype == "permission":
            decision = payload.get("decision")
            if decision in {"confirm", "override"}:
                gate_holds += 1
            elif decision == "allow":
                allow_calls += 1
            name = payload.get("tool_name")
            if isinstance(name, str) and name not in tools:
                tools.append(name)
        elif etype == "tool_call":
            tool_calls += 1
            summary = payload.get("result_summary")
            if isinstance(summary, str) and "ok=False" in summary:
                errors += 1
    return ScenarioTrace(
        scenario_id=scenario_id,
        trace_id=trace_id,
        tool_calls=tool_calls,
        gate_holds=gate_holds,
        allow_calls=allow_calls,
        errors=errors,
        tools=tuple(tools),
        error=error,
    )


def run_exercise(scenarios: list[ExerciseScenario] | None = None) -> FrictionReport:
    """Drive scenarios under tracing and distill a friction report.

    Enables tracing to a throwaway temp trace root for the duration and restores
    both the env var and the trace-store root afterward, so a run never pollutes
    the real store or leaks activation state. Fully fail-safe: a scenario whose
    drive raises is recorded (``ScenarioTrace.error``) rather than crashing the
    sweep.
    """
    scenarios = scenarios if scenarios is not None else offline_scenarios()

    from ..observability import local_trace_store, traces as traces_module

    prior_flag_present = "EVA_TRACING_ENABLED" in os.environ
    prior_flag_value = os.environ.get("EVA_TRACING_ENABLED")
    original_root = local_trace_store.DEFAULT_TRACE_ROOT
    temp_root = Path(tempfile.mkdtemp(prefix="eva_exercise_"))

    report = FrictionReport()
    try:
        os.environ["EVA_TRACING_ENABLED"] = "1"
        local_trace_store.DEFAULT_TRACE_ROOT = temp_root

        for scenario in scenarios:
            trace_id: str | None = None
            drive_error: str | None = None
            try:
                with task_trace(f"exercise:{scenario.id}", scenario.description) as active_trace_id:
                    trace_id = active_trace_id
                    scenario.drive(EvalContext.create())
            except Exception as exc:  # a broken scenario must never crash the sweep
                drive_error = f"{type(exc).__name__}: {exc}"

            events: list[dict] = []
            if trace_id:
                try:
                    events = traces_module.read_trace(trace_id, root=temp_root).get("events", [])
                except Exception:
                    events = []
            report.traces.append(_metrics_from_events(scenario.id, trace_id, events, drive_error))
    finally:
        local_trace_store.DEFAULT_TRACE_ROOT = original_root
        if prior_flag_present:
            os.environ["EVA_TRACING_ENABLED"] = prior_flag_value or ""
        else:
            os.environ.pop("EVA_TRACING_ENABLED", None)

    return report


def run_offline_exercise() -> FrictionReport:
    """Convenience: run the full offline, CI-safe exercise suite."""
    return run_exercise(offline_scenarios())
