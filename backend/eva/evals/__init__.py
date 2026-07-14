"""Objective task-eval harness (Phase 36b).

Offline, CI-safe, deterministic checks against the real tool gate and fast
command router, plus honest (gated, non-executing) adapter stubs for public
agent benchmarks.
"""

from __future__ import annotations

from .benchmarks import BenchmarkAdapter, benchmark_adapters
from .harness import EvalHarness, run_offline_evals
from .models import EvalContext, EvalReport, EvalResult, EvalTask
from .offline_suite import offline_tasks

__all__ = [
    "EvalTask",
    "EvalContext",
    "EvalResult",
    "EvalReport",
    "EvalHarness",
    "offline_tasks",
    "run_offline_evals",
    "BenchmarkAdapter",
    "benchmark_adapters",
]
