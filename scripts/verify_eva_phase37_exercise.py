from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    import backend.eva.observability.local_trace_store as local_trace_store
    from backend.eva.evals.exercise import offline_scenarios, run_offline_exercise
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry
    from scripts import verify_eva_all

    # Capture pre-run state so we can prove the harness leaks nothing.
    flag_present_before = "EVA_TRACING_ENABLED" in os.environ
    flag_value_before = os.environ.get("EVA_TRACING_ENABLED")
    root_before = local_trace_store.DEFAULT_TRACE_ROOT

    report = run_offline_exercise()

    check(report.scenarios >= 3, f"exercise ran too few scenarios: {report.scenarios}")
    check(report.total_tool_calls >= 1, "exercise executed no tools at all")
    check(report.total_gate_holds >= 1, "exercise recorded no gate-holds (the gated scenario should hold)")

    observe = next((t for t in report.traces if t.scenario_id == "observe_requires_confirmation"), None)
    check(observe is not None, "missing the observe_requires_confirmation scenario")
    check(observe.gate_holds >= 1, "the gated scenario recorded no gate-hold")
    check(observe.tool_calls == 0, "the gated scenario executed a tool (it must be held, not run)")

    # No pollution / no leak: env flag and trace-store root restored exactly.
    if flag_present_before:
        check(os.environ.get("EVA_TRACING_ENABLED") == flag_value_before, "EVA_TRACING_ENABLED value changed after exercise")
    else:
        check("EVA_TRACING_ENABLED" not in os.environ, "exercise leaked EVA_TRACING_ENABLED into the environment")
    check(local_trace_store.DEFAULT_TRACE_ROOT == root_before, "exercise did not restore the trace-store root")

    result = maybe_handle_fast_command("exercise run", ToolRegistry())
    check(result is not None, "exercise run fast-command did not route")
    check(isinstance(result[0], str) and result[0].strip(), "exercise run returned an empty report")

    verifier_name = "verify_eva_phase37_exercise.py"
    check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 37 exercise verifier")
    descriptors = getattr(verify_eva_all, "VERIFIER_DESCRIPTORS")
    check(verifier_name in descriptors, "master verifier descriptor missing the Phase 37 exercise verifier")

    print("PASS: Phase 37b exercise harness drives real scenarios under tracing, reports friction, holds gated tools, and leaks no tracing state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
