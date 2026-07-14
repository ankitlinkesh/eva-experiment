"""Executable spec for the objective task-eval harness (Phase 36b).

Covers: the offline suite is non-empty and fully passes against the real
tool gate/router; the report's arithmetic is internally consistent; the
harness never lets a broken task's check crash the sweep; and the public
benchmark adapters stay inert (unavailable, skipped) under the default
(unset) environment so CI never executes a public benchmark.
"""

from __future__ import annotations

from backend.eva.evals import EvalContext, EvalHarness, EvalTask, benchmark_adapters, offline_tasks, run_offline_evals


def test_offline_tasks_non_empty():
    tasks = offline_tasks()
    assert tasks, "offline_tasks() must return at least one task"


def test_run_offline_evals_all_passed():
    report = run_offline_evals()
    assert report.all_passed is True, report.summary_text()


def test_report_math_is_consistent():
    report = run_offline_evals()
    assert report.passed_count + report.failed_count == report.total
    assert 0.0 <= report.pass_rate <= 1.0
    if report.total:
        assert report.pass_rate == report.passed_count / report.total
    else:
        assert report.pass_rate == 0.0


def test_harness_catches_a_raising_check():
    def _boom(ctx: EvalContext) -> tuple[bool, str]:
        raise RuntimeError("deliberate failure")

    task = EvalTask(id="raises", description="a task whose check raises", category="test", check=_boom)
    report = EvalHarness().run([task])

    assert report.total == 1
    result = report.results[0]
    assert result.passed is False
    assert "RuntimeError" in result.detail
    assert "deliberate failure" in result.detail


def test_benchmark_adapters_are_inert_by_default(monkeypatch):
    for flag in (
        "EVA_BENCH_GAIA_PATH",
        "EVA_BENCH_WEBARENA_URL",
        "EVA_BENCH_OSWORLD_PATH",
        "EVA_BENCH_TAUBENCH_PATH",
    ):
        monkeypatch.delenv(flag, raising=False)

    adapters = benchmark_adapters()
    assert len(adapters) == 4
    for adapter in adapters:
        availability = adapter.availability()
        assert availability["available"] is False, f"{adapter.name} must be unavailable by default"
        result = adapter.run()
        assert result["status"] == "skipped", f"{adapter.name} must skip, not execute, by default"
