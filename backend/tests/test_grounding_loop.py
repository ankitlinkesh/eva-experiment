"""Agent-loop grounding integration (Phase 44).

Proves the situational snapshot actually reaches the planner and the event log
when perception is on/injected, and is a byte-identical no-op when it is off.
"""

from __future__ import annotations

import asyncio

from eva.agent.planner import PlannedToolCall, PlannerDecision
from eva.agent.runner import run_agentic_task
from eva.perception.situational_model import Situation
from eva.tools.registry import ToolRegistry


class _CapturingPlanner:
    """Records what the loop put in task_context['situation'] each step."""

    def __init__(self, decisions):
        self._decisions = list(decisions)
        self.calls = 0
        self.seen_situation = "unset"

    async def plan(self, goal, history, mode="agent_step", task_context=None):
        self.seen_situation = (task_context or {}).get("situation")
        decision = self._decisions[min(self.calls, len(self._decisions) - 1)]
        self.calls += 1
        return decision


_DONE = PlannerDecision(type="done", reason="x", tool_calls=[], final_response="ok", continue_after_tools=False)


def _run(planner, context_extra):
    ctx = {"planner": planner, "registry": ToolRegistry(), "execute_tools": True}
    ctx.update(context_extra)
    return asyncio.run(run_agentic_task("do a thing", ctx))


def test_injected_situation_reaches_planner_and_events():
    s = Situation(active_app="Code.exe", active_title="runner.py", open_apps=["Code.exe", "chrome.exe"], window_count=2, captured_at="t")
    planner = _CapturingPlanner([_DONE])
    result = _run(planner, {"situation": s})
    assert planner.seen_situation and "Code.exe" in planner.seen_situation
    assert any(e.get("type") == "grounding" for e in result.get("events", []))


def test_injected_string_situation_is_used_verbatim():
    planner = _CapturingPlanner([_DONE])
    _run(planner, {"situation": "Active app: Terminal"})
    assert planner.seen_situation == "Active app: Terminal"


def test_no_grounding_when_disabled(monkeypatch):
    monkeypatch.delenv("EVA_PERCEPTION_ENABLED", raising=False)
    planner = _CapturingPlanner([_DONE])
    result = _run(planner, {})  # no injection, perception off
    assert planner.seen_situation is None
    assert not any(e.get("type") == "grounding" for e in result.get("events", []))


def test_sensitive_injected_situation_is_redacted_before_planner():
    s = Situation(active_app="chrome.exe", active_title="Wells Fargo - Login", open_apps=["chrome.exe"], window_count=1, captured_at="t")
    planner = _CapturingPlanner([_DONE])
    _run(planner, {"situation": s})
    assert "Wells Fargo" not in planner.seen_situation
    assert "[private window]" in planner.seen_situation
