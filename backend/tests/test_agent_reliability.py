"""Executable spec for Phase 39 agent-loop reliability.

Phase 39a made backend/eva/agent/runner.py recover from a failed step instead
of dying on the first one: a blocked step is recorded and the loop attempts a
bounded number of replans before it gives up honestly. This spec drives
run_agentic_task() with a deterministic ScriptedPlanner (the injectable
testability seam in ``context["planner"]``) to prove both halves of that
contract: repeated failure stops early (and cleanly, via
"failure_budget_exceeded" rather than burning the whole step budget), and a
single failure followed by success still recovers to ok=True.

Fully offline and deterministic: no network, no live LLM, and tracing is left
off (EVA_TRACING_ENABLED is never set).
"""

from __future__ import annotations

import asyncio

from backend.eva.agent.planner import PlannedToolCall, PlannerDecision
from backend.eva.agent.policies import max_agent_steps, max_consecutive_failures
from backend.eva.agent.runner import run_agentic_task
from backend.eva.tools.registry import ToolRegistry


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


FAILING_DECISION = PlannerDecision(
    type="tool_calls",
    reason="x",
    tool_calls=[PlannedToolCall(tool="definitely_not_a_tool", args={})],
    final_response="",
    continue_after_tools=True,
)

DONE_DECISION = PlannerDecision(
    type="done",
    reason="done",
    tool_calls=[],
    final_response="All set.",
    continue_after_tools=False,
)


def _run(planner: ScriptedPlanner) -> dict:
    return asyncio.run(
        run_agentic_task(
            "multi step goal",
            {"planner": planner, "registry": ToolRegistry(), "execute_tools": True},
        )
    )


def test_always_failing_planner_stops_within_failure_budget_not_max_steps():
    planner = ScriptedPlanner([FAILING_DECISION])

    result = _run(planner)

    assert result["ok"] is False
    assert result["status"] == "failed"
    assert "failure_budget_exceeded" in result["safety_stops"]
    assert "max_steps_reached" not in result["safety_stops"]
    assert result["steps_count"] <= max_agent_steps()
    assert result["steps_count"] <= max_consecutive_failures() + 1


def test_fail_once_then_done_recovers():
    planner = ScriptedPlanner([FAILING_DECISION, DONE_DECISION])

    result = _run(planner)

    assert result["ok"] is True
    assert result["status"] == "done"
    assert "failure_budget_exceeded" not in result["safety_stops"]
    assert "All set." in result["final_response"]


def test_immediate_done_planner_succeeds():
    planner = ScriptedPlanner([DONE_DECISION])

    result = _run(planner)

    assert result["ok"] is True
    assert result["status"] == "done"
