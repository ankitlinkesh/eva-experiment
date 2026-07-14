"""Tests for the Phase 40c least-privilege per-task tool scope.

Two layers: the pure ``TaskToolScope`` matching semantics, and an end-to-end
proof that ``run_agentic_task`` actually enforces ``context["tool_scope"]`` —
a planned tool outside the scope is denied before it runs, no matter what the
(scripted, deterministic) planner proposed.
"""

from __future__ import annotations

import asyncio

from backend.eva.agent.planner import PlannedToolCall, PlannerDecision
from backend.eva.agent.runner import run_agentic_task
from backend.eva.threat_defense.tool_scope import TaskToolScope
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


def test_unrestricted_scope_allows_anything():
    scope = TaskToolScope.of(None)

    assert scope.restricted is False
    assert scope.is_allowed("workspace_status") is True
    assert scope.is_allowed("file.delete") is True
    assert scope.is_allowed("literally_anything_goes_here") is True


def test_restricted_list_allows_exact_and_wildcard_matches_only():
    scope = TaskToolScope.of(["workspace_status", "web.*"])

    assert scope.restricted is True
    assert scope.is_allowed("workspace_status") is True
    assert scope.is_allowed("web.open_url") is True
    assert scope.is_allowed("file.delete") is False


def test_empty_iterable_scope_is_restricted_and_allows_nothing():
    scope = TaskToolScope.of([])

    assert scope.restricted is True
    assert scope.is_allowed("workspace_status") is False
    assert scope.is_allowed("anything") is False


def test_single_string_scope_allows_only_that_tool():
    scope = TaskToolScope.of("only_this")

    assert scope.restricted is True
    assert scope.is_allowed("only_this") is True
    assert scope.is_allowed("only_this_other") is False
    assert scope.is_allowed("workspace_status") is False


def test_wildcard_prefix_matching():
    scope = TaskToolScope.of(["file.*"])

    assert scope.is_allowed("file.delete") is True
    assert scope.is_allowed("file.write_text") is True
    assert scope.is_allowed("workspace_status") is False


DELETE_DECISION = PlannerDecision(
    type="tool_calls",
    reason="clean up",
    tool_calls=[PlannedToolCall(tool="file.delete", args={"path": "C:/tmp/x.txt"})],
    final_response="",
    continue_after_tools=True,
)

STATUS_DECISION = PlannerDecision(
    type="tool_calls",
    reason="check status",
    tool_calls=[PlannedToolCall(tool="workspace_status", args={})],
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


def test_out_of_scope_tool_is_denied_end_to_end():
    planner = ScriptedPlanner([DELETE_DECISION])

    result = asyncio.run(
        run_agentic_task(
            "delete a file",
            {
                "planner": planner,
                "registry": ToolRegistry(),
                "tool_scope": ["workspace_status"],
                "execute_tools": True,
            },
        )
    )

    assert result["status"] == "failed"
    assert "out_of_scope:file.delete" in result["safety_stops"]
    assert "file.delete" not in result["tools_executed"]
    assert "file.delete" not in result["tools_planned"] or "file.delete" not in result["tools_executed"]


def test_in_scope_tool_still_succeeds():
    planner = ScriptedPlanner([STATUS_DECISION, DONE_DECISION])

    result = asyncio.run(
        run_agentic_task(
            "check status",
            {
                "planner": planner,
                "registry": ToolRegistry(),
                "tool_scope": ["workspace_status"],
                "execute_tools": True,
            },
        )
    )

    assert result["status"] == "done"
    assert result["ok"] is True
    assert "workspace_status" in result["tools_executed"]
    assert not any(str(stop).startswith("out_of_scope:") for stop in result["safety_stops"])
