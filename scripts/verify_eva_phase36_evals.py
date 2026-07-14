from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.evals import benchmark_adapters, offline_tasks, run_offline_evals
    from scripts import verify_eva_all

    report = run_offline_evals()
    check(report.all_passed, f"offline eval suite is not fully passing: {report.summary_text()}")
    check(report.total >= 5, f"offline eval suite has fewer than 5 tasks: {report.total}")

    tasks = offline_tasks()
    by_id = {task.id for task in tasks}
    for required_id in ("self_approval_is_ignored", "gated_tool_requires_confirmation"):
        check(required_id in by_id, f"security eval task missing from offline_tasks(): {required_id}")

    results_by_id = {result.task_id: result for result in report.results}
    for required_id in ("self_approval_is_ignored", "gated_tool_requires_confirmation"):
        result = results_by_id.get(required_id)
        check(result is not None, f"security eval task did not produce a result: {required_id}")
        check(result.passed, f"security eval task did not pass: {required_id}: {result.detail}")

    adapters = benchmark_adapters()
    check(len(adapters) >= 4, "benchmark_adapters() must expose at least GAIA/WebArena/OSWorld/tau-bench")
    for adapter in adapters:
        availability = adapter.availability()
        check(availability.get("available") is False, f"benchmark adapter must be unavailable under default env: {adapter.name}")
        result = adapter.run()
        check(result.get("status") == "skipped", f"benchmark adapter must skip under default env: {adapter.name}")

    verifier_name = "verify_eva_phase36_evals.py"
    check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile is missing the Phase 36b evals verifier")
    check(hasattr(verify_eva_all, "VERIFIER_DESCRIPTORS"), "master verifier descriptors missing")
    descriptors = getattr(verify_eva_all, "VERIFIER_DESCRIPTORS")
    check(verifier_name in descriptors, "master verifier descriptor missing the Phase 36b evals verifier")

    print("PASS: Phase 36b objective task-eval harness passes offline, enforces the security evals, and keeps public benchmark adapters inert by default.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
