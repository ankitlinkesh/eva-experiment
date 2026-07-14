from __future__ import annotations

import json
from typing import Any

from ..core.config import ModelSettings
from ..core.web_context import remember_web_results
from ..observability.context import task_trace
from ..tools.registry import ToolRegistry
from .cognition import build_initial_plan, reflect_on_step
from .executor import ToolExecutor, ToolExecutionResult
from .planner import PlannedToolCall, PlannerError, ToolCallPlanner
from .policies import (
    POWER_TOOLS,
    agentic_goal,
    describe_tool_observation,
    explicitly_requests_screen,
    is_unsupported_capability,
    max_agent_steps,
    max_screen_captures_per_task,
    max_tools_per_task,
    max_web_searches_per_task,
    tool_signature,
)
from .state import AgentRunState
from .task import AgentStep, AgentTask


def _safe_log(memory: Any, session_id: str | None, kind: str, payload: dict[str, Any]) -> None:
    if memory is None or not session_id:
        return
    try:
        memory.log_event(session_id, kind, payload)
    except Exception:
        return


def _compact_tool_result(result: ToolExecutionResult) -> dict[str, Any]:
    payload = result.as_dict()
    raw = payload.get("result")
    if isinstance(raw, dict) and "results" in raw and isinstance(raw["results"], list):
        payload["result"] = {
            **raw,
            "results": raw["results"][:5],
        }
    return payload


def _provenance_suffix(verification: dict[str, Any] | None) -> str:
    """Short suffix so Eva never narrates an unproven action as plain done.

    Mirrors the provenance classes from ``postconditions.py``: only an
    ``independent`` + verified effect earns an unqualified "(verified)"; every
    weaker class says so plainly instead of upgrading into a false claim of
    success. The independent-and-NOT-verified case never reaches here — the
    executor already demotes ``ok`` to False for that, routing it to the
    failure branch in :func:`_observation_text` instead.
    """
    if not verification:
        return ""
    provenance = verification.get("provenance")
    if provenance == "independent" and verification.get("verified"):
        return " (verified)"
    if provenance == "self_reported":
        return " (self-reported)"
    if provenance == "observed":
        return " (unverified — please confirm the visible result)"
    if provenance == "unverified":
        return " (unverified)"
    return ""


def _observation_text(call: PlannedToolCall, result: ToolExecutionResult) -> str:
    if result.requires_confirmation:
        return f"{call.tool} requires confirmation before {result.action or 'continuing'}."
    if not result.ok:
        return f"{call.tool} failed: {result.error or 'unknown error'}"
    return describe_tool_observation(call.tool, result.result) + _provenance_suffix(result.verification)


def _planned_tools(task: AgentTask) -> list[str]:
    return [step.tool_name for step in task.steps if step.tool_name]


def _executed_tools(task: AgentTask) -> list[str]:
    return [step.tool_name for step in task.steps if step.tool_name and step.status == "done"]


def _final_result(task: AgentTask, *, ok: bool, requires_confirmation: bool = False, action: str | None = None, events: list[dict[str, Any]] | None = None, safety_stops: list[str] | None = None) -> dict[str, Any]:
    return {
        "ok": ok,
        "task_id": task.id,
        "status": task.status,
        "final_response": task.final_response,
        "requires_confirmation": requires_confirmation,
        "action": action,
        "steps_count": len(task.steps),
        "tools_planned": _planned_tools(task),
        "tools_executed": _executed_tools(task),
        "safety_stops": safety_stops or [],
        "task": task.as_dict(),
        "events": events or [],
    }


def _store_task_state(session_context: Any, result: dict[str, Any]) -> None:
    if not isinstance(session_context, dict):
        return
    session_context["last_agent_task"] = {
        "task_id": result.get("task_id"),
        "status": result.get("status"),
        "steps_count": result.get("steps_count"),
        "tools_planned": result.get("tools_planned"),
        "tools_executed": result.get("tools_executed"),
        "last_observation": (result.get("task") or {}).get("observations", [])[-1:] if isinstance(result.get("task"), dict) else [],
        "final_response": result.get("final_response"),
        "requires_confirmation": result.get("requires_confirmation"),
        "action": result.get("action"),
        "safety_stops": result.get("safety_stops"),
    }
    session_context["active_task_status"] = result.get("status")


def _return_task(task: AgentTask, session_context: Any, **kwargs: Any) -> dict[str, Any]:
    result = _final_result(task, **kwargs)
    _store_task_state(session_context, result)
    return result


async def run_agentic_task(user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    raw_settings = context.get("settings")
    settings = getattr(raw_settings, "models", raw_settings) or ModelSettings()
    registry: ToolRegistry = context.get("registry") or ToolRegistry()
    executor: ToolExecutor = context.get("executor") or ToolExecutor(registry)
    memory = context.get("memory")
    session_id = context.get("session_id")
    session_context = context.get("session_context")
    history = context.get("history") or []
    execute_tools = bool(context.get("execute_tools", True))

    goal = agentic_goal(user_message)
    with task_trace(str(session_id or "").strip() or "agent-task", goal) as _trace_id:
        task = AgentTask(
            user_goal=goal,
            max_steps=max_agent_steps(),
            max_tool_calls=max_tools_per_task(),
            max_web_searches=max_web_searches_per_task(),
            max_screen_captures=max_screen_captures_per_task(),
        )
        task.plan = build_initial_plan(goal)
        state = AgentRunState()
        planner = ToolCallPlanner(settings, registry)
        events: list[dict[str, Any]] = [
            {"type": "agent_task", "task_id": task.id, "message": "Agent task started"},
            {"type": "agent_plan", "task_id": task.id, "plan": list(task.plan), "message": "Plan ready"},
        ]
        safety_stops: list[str] = []

        _safe_log(memory, session_id, "agent_task_started", {"task_id": task.id, "goal": goal, "plan": list(task.plan)})

        if is_unsupported_capability(goal):
            task.status = "failed"
            task.final_response = "I cannot complete that safely yet because the needed module is not available."
            safety_stops.append("unsupported_capability")
            _safe_log(memory, session_id, "agent_task_failed", {"task_id": task.id, "reason": "unsupported_capability"})
            return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)

        for index in range(1, task.max_steps + 1):
            task.status = "planning"
            events.append({"type": "agent_step", "task_id": task.id, "step": index, "message": f"Step {index}: planning"})
            task_context = {
                "goal": goal,
                "plan": list(task.plan),
                "observations": list(task.observations),
                "reflections": [reflection.as_dict() for reflection in task.reflections[-4:]],
                "steps": [step.as_dict() for step in task.steps],
                "limits": {
                    "max_steps": task.max_steps,
                    "max_tool_calls": task.max_tool_calls,
                    "max_web_searches": task.max_web_searches,
                    "max_screen_captures": task.max_screen_captures,
                    "tool_calls_used": state.tool_calls,
                    "web_searches_used": state.web_searches,
                    "screen_captures_used": state.screen_captures,
                },
            }

            try:
                decision = await planner.plan(goal, history, mode="agent_step", task_context=task_context)
            except PlannerError as exc:
                state.record_invalid_json()
                _safe_log(memory, session_id, "agent_planner_error", {"task_id": task.id, "step": index, "error": str(exc)})
                if state.invalid_json_errors >= 2:
                    task.status = "failed"
                    task.final_response = "I could not plan this safely after two attempts. Try a simpler task."
                    safety_stops.append("planner_invalid_json_twice")
                    return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)
                continue

            _safe_log(
                memory,
                session_id,
                "agent_step_planned",
                {
                    "task_id": task.id,
                    "step": index,
                    "decision": {
                        "type": decision.type,
                        "reason": decision.reason,
                        "tool_calls": [{"tool": call.tool, "args": call.args} for call in decision.tool_calls],
                        "continue_after_tools": decision.continue_after_tools,
                    },
                },
            )

            if decision.type in {"answer", "done"}:
                step = AgentStep(index=index, thought_summary=decision.reason, planned_action=decision.type, observation=decision.final_response, status="done")
                task.add_step(step)
                task.status = "done"
                task.final_response = decision.final_response
                events.append({"type": "agent_step", "task_id": task.id, "step": index, "message": f"Step {index}: done"})
                _safe_log(memory, session_id, "agent_task_done", {"task_id": task.id, "final_response": task.final_response})
                return _return_task(task, session_context, ok=True, events=events, safety_stops=safety_stops)

            if decision.type == "confirmation_required":
                step = AgentStep(index=index, thought_summary=decision.reason, planned_action="confirmation_required", observation=decision.final_response, status="skipped")
                task.add_step(step)
                task.status = "waiting_for_confirmation"
                task.final_response = decision.final_response
                events.append({"type": "agent_step", "task_id": task.id, "step": index, "message": f"Step {index}: confirmation required"})
                _safe_log(memory, session_id, "agent_task_waiting_for_confirmation", {"task_id": task.id, "action": decision.action, "message": decision.final_response})
                return _return_task(task, session_context, ok=False, requires_confirmation=True, action=decision.action, events=events, safety_stops=safety_stops)

            call = decision.tool_calls[0]
            step = AgentStep(index=index, thought_summary=decision.reason, planned_action="tool_calls", tool_name=call.tool, tool_args=call.args, status="running")
            task.add_step(step)
            events.append({"type": "agent_step", "task_id": task.id, "step": index, "message": f"Step {index}: tool {call.tool}"})

            if state.tool_calls >= task.max_tool_calls:
                step.status = "failed"
                step.error = "tool_limit_reached"
                task.status = "failed"
                task.final_response = "I stopped because the tool-call limit was reached."
                safety_stops.append("tool_limit_reached")
                return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)

            if call.tool in {"web_search", "research_web", "browser_search"} and state.web_searches >= task.max_web_searches:
                step.status = "failed"
                step.error = "web_search_limit_reached"
                task.status = "failed"
                task.final_response = "I stopped because the web-search limit was reached."
                safety_stops.append("web_search_limit_reached")
                return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)

            if call.tool in {"capture_screen", "analyze_screen"} or (call.tool == "desktop_observe" and bool(call.args.get("include_screen"))):
                if not explicitly_requests_screen(goal):
                    step.status = "failed"
                    step.error = "screen_capture_not_explicit"
                    task.status = "failed"
                    task.final_response = "I did not capture the screen because you did not explicitly ask me to inspect it."
                    safety_stops.append("screen_capture_not_explicit")
                    return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)
                if state.screen_captures >= task.max_screen_captures:
                    step.status = "failed"
                    step.error = "screen_capture_limit_reached"
                    task.status = "failed"
                    task.final_response = "I stopped because the screen-capture limit was reached."
                    safety_stops.append("screen_capture_limit_reached")
                    return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)

            if call.tool in POWER_TOOLS:
                step.status = "skipped"
                step.observation = "Power actions require confirmation."
                task.add_observation(step.observation)
                task.status = "waiting_for_confirmation"
                task.final_response = "This power action requires confirmation before I can continue."
                events.append({"type": "agent_observation", "task_id": task.id, "step": index, "message": step.observation})
                return _return_task(task, session_context, ok=False, requires_confirmation=True, action=str(call.args.get("action") or "power_action"), events=events, safety_stops=safety_stops)

            if state.repeated_without_progress(call):
                step.status = "failed"
                step.error = "repeated_action_without_progress"
                task.status = "failed"
                task.final_response = "I stopped because the same action repeated without a new observation."
                safety_stops.append(f"repeated_action:{tool_signature(call)}")
                return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)

            state.record_tool(call)

            if not execute_tools:
                step.status = "skipped"
                step.observation = f"Dry run: planned {call.tool} with args {json.dumps(call.args, ensure_ascii=False)}."
                task.add_observation(step.observation)
                task.status = "done"
                task.final_response = step.observation
                events.append({"type": "agent_observation", "task_id": task.id, "step": index, "message": step.observation})
                _safe_log(memory, session_id, "agent_tool_dry_run", {"task_id": task.id, "step": index, "tool": call.tool, "args": call.args})
                return _return_task(task, session_context, ok=True, events=events, safety_stops=safety_stops)

            result = executor.execute(call)
            if call.tool in {"web_search", "browser_search"} and result.ok:
                remember_web_results(session_context, result.result)
            observation = _observation_text(call, result)
            step.observation = observation
            step.status = "done" if result.ok else "failed"
            step.error = result.error
            task.add_observation(observation)
            events.append({"type": "agent_observation", "task_id": task.id, "step": index, "message": observation})
            task.status = "reflecting"
            reflection = reflect_on_step(goal, task, step, result)
            task.add_reflection(reflection)
            events.append(
                {
                    "type": "agent_reflection",
                    "task_id": task.id,
                    "step": index,
                    "message": reflection.summary,
                    "status": reflection.status,
                    "confidence": reflection.confidence,
                    "next_focus": reflection.next_focus,
                }
            )
            _safe_log(memory, session_id, "agent_tool_executed", {"task_id": task.id, "step": index, "tool": call.tool, "args": call.args, "result": _compact_tool_result(result)})
            _safe_log(memory, session_id, "agent_step_reflection", {"task_id": task.id, "step": index, "reflection": reflection.as_dict()})

            if reflection.status == "blocked":
                task.status = "failed"
                task.final_response = observation
                safety_stops.append("reflection_blocked")
                _safe_log(memory, session_id, "agent_task_failed", {"task_id": task.id, "reason": "reflection_blocked", "observation": observation})
                return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)

            if reflection.status == "needs_confirmation":
                task.status = "waiting_for_confirmation"
                task.final_response = result.error or "This action requires confirmation."
                return _return_task(task, session_context, ok=False, requires_confirmation=True, action=result.action, events=events, safety_stops=safety_stops)

            if call.tool in {"web_search", "research_web", "browser_search"} and result.ok and _web_summary_goal_without_open(goal):
                task.status = "done"
                task.final_response = observation
                _safe_log(memory, session_id, "agent_task_done", {"task_id": task.id, "reason": "web_summary_complete", "final_response": task.final_response})
                return _return_task(task, session_context, ok=True, events=events, safety_stops=safety_stops)

            if result.requires_confirmation:
                task.status = "waiting_for_confirmation"
                task.final_response = result.error or "This action requires confirmation."
                return _return_task(task, session_context, ok=False, requires_confirmation=True, action=result.action, events=events, safety_stops=safety_stops)

            if call.tool in {"capture_screen", "analyze_screen"} and not result.ok:
                task.status = "failed"
                task.final_response = observation
                safety_stops.append("screen_tool_failed")
                _safe_log(memory, session_id, "agent_task_failed", {"task_id": task.id, "reason": "screen_tool_failed", "observation": observation})
                return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)

            if call.tool == "analyze_screen" and isinstance(result.result, dict) and not result.result.get("ok", True):
                task.status = "failed"
                task.final_response = observation
                safety_stops.append("screen_analysis_failed")
                _safe_log(memory, session_id, "agent_task_failed", {"task_id": task.id, "reason": "screen_analysis_failed", "observation": observation})
                return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)

            if not decision.continue_after_tools:
                task.status = "done"
                task.final_response = observation
                _safe_log(memory, session_id, "agent_task_done", {"task_id": task.id, "final_response": task.final_response})
                return _return_task(task, session_context, ok=True, events=events, safety_stops=safety_stops)

        task.status = "failed"
        task.final_response = "I reached my maximum step limit, so I stopped with the progress I had."
        safety_stops.append("max_steps_reached")
        _safe_log(memory, session_id, "agent_task_failed", {"task_id": task.id, "reason": "max_steps_reached", "observations": task.observations})
        return _return_task(task, session_context, ok=False, events=events, safety_stops=safety_stops)


def _web_summary_goal_without_open(goal: str) -> bool:
    text = " ".join(goal.lower().split())
    wants_web_summary = any(marker in text for marker in ("find", "summarize", "research", "compare", "search", "best"))
    explicitly_opens = any(marker in text for marker in ("open result", "open the", "open first", "open chrome", "open browser", "open url"))
    return wants_web_summary and not explicitly_opens
