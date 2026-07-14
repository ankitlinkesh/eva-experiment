"""Runner for objective eval tasks (Phase 36b).

The harness is deliberately dumb: it times each task, runs its check inside a
flight-recorder trace scope (inert unless ``EVA_TRACING_ENABLED`` is set —
see :mod:`backend.eva.observability.context`), and never lets a broken task
crash the sweep. A check that raises is recorded as a failed result, not a
harness-level exception, so one bad task cannot hide the rest of the report.
"""

from __future__ import annotations

import time

from ..observability.context import task_trace
from .models import EvalContext, EvalReport, EvalResult, EvalTask


class EvalHarness:
    """Runs a list of :class:`EvalTask` against a shared or fresh context."""

    def run(self, tasks: list[EvalTask], ctx: EvalContext | None = None) -> EvalReport:
        context = ctx or EvalContext.create()
        results: list[EvalResult] = []
        for task in tasks:
            start = time.perf_counter()
            trace_id: str | None = None
            try:
                with task_trace(f"eval:{task.id}", task.description) as active_trace_id:
                    trace_id = active_trace_id
                    passed, detail = task.check(context)
            except Exception as exc:  # a broken task must never crash the harness
                passed, detail = False, f"raised {type(exc).__name__}: {exc}"
            duration_ms = (time.perf_counter() - start) * 1000.0
            results.append(
                EvalResult(
                    task_id=task.id,
                    category=task.category,
                    passed=passed,
                    detail=detail,
                    duration_ms=duration_ms,
                    trace_id=trace_id,
                )
            )
        return EvalReport(results=results)


def run_offline_evals() -> EvalReport:
    """Convenience entry point: run the full offline, CI-safe suite."""
    from .offline_suite import offline_tasks

    return EvalHarness().run(offline_tasks())
