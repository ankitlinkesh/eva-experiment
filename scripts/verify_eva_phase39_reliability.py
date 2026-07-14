from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


class ScriptedPlanner:
    """Deterministic planner for driving the agent loop in tests. Returns queued
    PlannerDecisions in order; repeats the last one once exhausted."""

    def __init__(self, decisions):
        self._decisions = list(decisions)
        self.calls = 0

    async def plan(self, goal, history, mode="agent_step", task_context=None):
        decision = self._decisions[min(self.calls, len(self._decisions) - 1)]
        self.calls += 1
        return decision


def main() -> int:
    from backend.eva.agent.planner import PlannedToolCall, PlannerDecision
    from backend.eva.agent.policies import max_agent_steps, max_consecutive_failures
    from backend.eva.agent.runner import run_agentic_task
    from backend.eva.agent.state import AgentRunState
    from backend.eva.evals.harness import run_offline_evals
    from backend.eva.evals.offline_suite import offline_tasks
    from backend.eva.tools.registry import ToolRegistry
    from scripts import verify_eva_all

    failing = PlannerDecision(
        type="tool_calls",
        reason="x",
        tool_calls=[PlannedToolCall(tool="definitely_not_a_tool", args={})],
        final_response="",
        continue_after_tools=True,
    )
    done = PlannerDecision(
        type="done",
        reason="done",
        tool_calls=[],
        final_response="All set.",
        continue_after_tools=False,
    )

    # 1. An always-failing planner must recover a bounded number of times, then
    #    stop honestly via the failure budget -- never by burning every step.
    always_fail = asyncio.run(
        run_agentic_task(
            "multi step goal",
            {"planner": ScriptedPlanner([failing]), "registry": ToolRegistry(), "execute_tools": True},
        )
    )
    check(always_fail["ok"] is False, f"always-failing planner must report ok=False, got {always_fail['ok']!r}")
    check(always_fail["status"] == "failed", f"always-failing planner must report status=failed, got {always_fail['status']!r}")
    check(
        "failure_budget_exceeded" in always_fail["safety_stops"],
        f"always-failing planner must stop via failure_budget_exceeded, got {always_fail['safety_stops']!r}",
    )
    check(
        "max_steps_reached" not in always_fail["safety_stops"],
        f"always-failing planner must not fall through to max_steps_reached, got {always_fail['safety_stops']!r}",
    )
    check(
        always_fail["steps_count"] <= max_consecutive_failures() + 1,
        f"always-failing planner must stop quickly (<= max_consecutive_failures()+1 steps), got {always_fail['steps_count']!r}",
    )

    # 2. A single failure followed by a successful "done" step must recover.
    recovers = asyncio.run(
        run_agentic_task(
            "multi step goal",
            {"planner": ScriptedPlanner([failing, done]), "registry": ToolRegistry(), "execute_tools": True},
        )
    )
    check(recovers["ok"] is True, f"fail-then-done planner must recover to ok=True, got {recovers['ok']!r}")
    check(recovers["status"] == "done", f"fail-then-done planner must recover to status=done, got {recovers['status']!r}")
    check(
        "failure_budget_exceeded" not in recovers["safety_stops"],
        f"a recovered task must not carry a failure_budget_exceeded stop, got {recovers['safety_stops']!r}",
    )
    check("All set." in recovers["final_response"], f"recovered task must reach the done decision's final_response, got {recovers['final_response']!r}")

    # 3. AgentRunState bookkeeping: failure/success/stall semantics.
    state = AgentRunState()
    state.record_failure("first")
    check(state.failure_budget_exceeded(2) is False, "one failure must not exceed a budget of 2")
    state.record_failure("second")
    check(state.failure_budget_exceeded(2) is True, "two consecutive failures must exceed a budget of 2")
    state.record_success()
    check(state.failure_budget_exceeded(2) is False, "a success must reset the failure streak")
    check(state.consecutive_failures == 0, "record_success must zero consecutive_failures")
    check(state.steps_since_progress == 0, "record_success must zero steps_since_progress")

    stall_state = AgentRunState()
    stall_state.record_failure("a")
    stall_state.record_failure("b")
    check(stall_state.stalled(3) is False, "two steps without progress must not stall a limit of 3")
    stall_state.record_failure("c")
    check(stall_state.stalled(3) is True, "three steps without progress must stall a limit of 3")

    # 4. Policy budgets: sane defaults, honoring an env override.
    check(max_consecutive_failures() >= 1, "max_consecutive_failures() must be at least 1")
    check(max_agent_steps() >= 1, "max_agent_steps() must be at least 1")
    original_env = os.environ.get("EVA_AGENT_MAX_CONSECUTIVE_FAILURES")
    try:
        os.environ["EVA_AGENT_MAX_CONSECUTIVE_FAILURES"] = "5"
        check(max_consecutive_failures() == 5, "max_consecutive_failures() must honor its env override")
    finally:
        if original_env is None:
            os.environ.pop("EVA_AGENT_MAX_CONSECUTIVE_FAILURES", None)
        else:
            os.environ["EVA_AGENT_MAX_CONSECUTIVE_FAILURES"] = original_env

    # 5. The reliability eval is registered and the offline suite stays green.
    task_ids = {task.id for task in offline_tasks()}
    check("agent_recovers_or_stops_within_budget" in task_ids, "the reliability eval must be registered in the offline suite")
    report = run_offline_evals()
    check(report.all_passed, f"offline eval suite must stay green: {report.summary_text()}")
    check(
        any(r.task_id == "agent_recovers_or_stops_within_budget" and r.passed for r in report.results),
        "the reliability eval must pass",
    )

    # 6. The runner wiring actually exists (not just the tests exercising it).
    runner_source = (ROOT / "backend" / "eva" / "agent" / "runner.py").read_text(encoding="utf-8")
    check("failure_budget_exceeded" in runner_source, "runner.py must call state.failure_budget_exceeded")
    check("record_failure" in runner_source, "runner.py must call state.record_failure")
    check("max_consecutive_failures" in runner_source, "runner.py must import/use max_consecutive_failures")

    # 7. Registered in the master verifier profiles.
    verifier_name = "verify_eva_phase39_reliability.py"
    check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 39 reliability verifier")
    descriptors = getattr(verify_eva_all, "VERIFIER_DESCRIPTORS")
    check(verifier_name in descriptors, "master verifier descriptor missing the Phase 39 reliability verifier")

    os.environ.pop("EVA_TRACING_ENABLED", None)
    print("PASS: Phase 39 agent loop recovers from a failed step and retries, then stops honestly within a bounded failure budget (never max_steps_reached); a fail-then-succeed run still reaches ok=True; AgentRunState/policies bookkeeping and env overrides behave; the reliability eval is registered and green; and the verifier is wired into the master profiles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
