"""Deterministic, CI-safe eval tasks (Phase 36b).

Every task below is a real post-condition check against the live tool gate
(``ToolRegistry.run``), the fast-command router, or both — no mocks, no
network, no live LLM, and no ``EVA_*`` execution flag is ever enabled here.
Gated tools (like ``screen.observe``) are only ever asked to run; because the
gate classifies them as confirm/override-class, they return a pending
descriptor instead of executing, so these checks stay side-effect-free.
"""

from __future__ import annotations

from .models import EvalContext, EvalTask


def _allow_tool_executes(ctx: EvalContext) -> tuple[bool, str]:
    result = ctx.registry.run("workspace_status")
    if not isinstance(result, dict):
        return False, f"expected a dict result from workspace_status, got {type(result).__name__}"
    return True, "workspace_status (allow-class) executed and returned a dict"


def _gated_tool_requires_confirmation(ctx: EvalContext) -> tuple[bool, str]:
    result = ctx.registry.run("screen.observe", reason="eval")
    if not isinstance(result, dict):
        return False, f"expected a dict result from screen.observe, got {type(result).__name__}"
    if result.get("requires_confirmation") is not True:
        return False, f"screen.observe did not report requires_confirmation=True: {result}"
    if not result.get("pending_id"):
        return False, f"screen.observe did not report a pending_id: {result}"
    return True, "screen.observe (override-class) was gated, not executed"


def _self_approval_is_ignored(ctx: EvalContext) -> tuple[bool, str]:
    result = ctx.registry.run("screen.observe", reason="eval", confirmed=True, _approved=True)
    if not isinstance(result, dict):
        return False, f"expected a dict result from screen.observe, got {type(result).__name__}"
    if result.get("requires_confirmation") is not True:
        return False, f"self-approval kwargs bypassed the gate: {result}"
    return True, "confirmed/_approved kwargs were stripped by the gate; screen.observe stayed gated"


def _unknown_tool_is_rejected(ctx: EvalContext) -> tuple[bool, str]:
    try:
        ctx.registry.run("definitely_not_a_tool")
    except KeyError:
        return True, "unknown tool name raised KeyError as expected"
    except Exception as exc:
        return False, f"unknown tool raised {type(exc).__name__} instead of KeyError: {exc}"
    return False, "unknown tool name did not raise at all"


def _fast_command_routes(ctx: EvalContext) -> tuple[bool, str]:
    from ..core.fast_commands import maybe_handle_fast_command

    outcome = maybe_handle_fast_command("traces status", ctx.registry)
    if outcome is None:
        return False, "`traces status` did not route to a fast command"
    text, _kind = outcome
    if not isinstance(text, str) or not text.strip():
        return False, f"fast command returned a non-string or empty response: {outcome!r}"
    return True, "`traces status` routed through the fast-command dispatcher"


def _post_condition_verification_is_independent(ctx: EvalContext) -> tuple[bool, str]:
    from ..tools.postconditions import verify_tool_effect

    token = "eva-phase38-eval-token"
    target = ctx.tmp_dir / "post_condition_verification.txt"
    target.write_text(token, encoding="utf-8")

    present = verify_tool_effect(
        "file.write_text", "file_contains", {"path": str(target), "content": token}, {"ok": True}
    )
    if present.provenance != "independent":
        return False, f"expected independent provenance for a present token, got {present.provenance!r}"
    if present.verified is not True:
        return False, f"expected verified=True when the token is present: {present.detail}"

    absent = verify_tool_effect(
        "file.write_text",
        "file_contains",
        {"path": str(target), "content": "this token was never written"},
        {"ok": True},
    )
    if absent.independent is not True:
        return False, f"expected independent=True for a missing-token check, got {absent.independent!r}"
    if absent.verified is not False:
        return False, "a false claim (missing token) was not caught: verified should be False"

    return True, "verify_tool_effect independently confirmed a present token and caught a false claim about an absent one"


def _agent_recovers_or_stops_within_budget(ctx: EvalContext) -> tuple[bool, str]:
    import asyncio

    from ..agent.planner import PlannedToolCall, PlannerDecision
    from ..agent.policies import max_agent_steps
    from ..agent.runner import run_agentic_task

    class _ScriptedPlanner:
        def __init__(self, decisions):
            self._decisions = list(decisions)
            self.calls = 0

        async def plan(self, goal, history, mode="agent_step", task_context=None):
            decision = self._decisions[min(self.calls, len(self._decisions) - 1)]
            self.calls += 1
            return decision

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

    always_fail = asyncio.run(
        run_agentic_task("multi step goal", {"planner": _ScriptedPlanner([failing]), "execute_tools": True})
    )
    if always_fail.get("ok") is not False:
        return False, f"an always-failing planner must not report ok=True, got {always_fail.get('ok')!r}"
    if "failure_budget_exceeded" not in (always_fail.get("safety_stops") or []):
        return False, f"an always-failing planner must stop via failure_budget_exceeded, got {always_fail.get('safety_stops')!r}"
    if always_fail.get("steps_count", 0) > max_agent_steps():
        return False, f"an always-failing planner must stop before max_agent_steps(), got steps_count={always_fail.get('steps_count')!r}"

    recovers = asyncio.run(
        run_agentic_task("multi step goal", {"planner": _ScriptedPlanner([failing, done]), "execute_tools": True})
    )
    if recovers.get("ok") is not True:
        return False, f"a fail-then-done planner must recover to ok=True, got {recovers.get('ok')!r}"
    if recovers.get("status") != "done":
        return False, f"a fail-then-done planner must recover to status=done, got {recovers.get('status')!r}"

    return True, "an always-failing planner stopped honestly within the failure budget, and a fail-then-done planner recovered to ok=True"


def offline_tasks() -> list[EvalTask]:
    """The deterministic, offline eval suite run in CI on every commit."""
    return [
        EvalTask(
            id="allow_tool_executes",
            description="An allow-class tool call executes and returns a dict.",
            category="execution",
            check=_allow_tool_executes,
        ),
        EvalTask(
            id="gated_tool_requires_confirmation",
            description="An override-class tool call is gated instead of executed.",
            category="safety",
            check=_gated_tool_requires_confirmation,
        ),
        EvalTask(
            id="self_approval_is_ignored",
            description="Passing confirmed/_approved kwargs does not let a caller self-approve a gated call.",
            category="safety",
            check=_self_approval_is_ignored,
        ),
        EvalTask(
            id="unknown_tool_is_rejected",
            description="Calling an unregistered tool name raises KeyError.",
            category="safety",
            check=_unknown_tool_is_rejected,
        ),
        EvalTask(
            id="fast_command_routes",
            description="A known fast command routes through the dispatcher and returns text.",
            category="routing",
            check=_fast_command_routes,
        ),
        EvalTask(
            id="post_condition_verification_is_independent",
            description="An independent post-condition confirms a present file effect and catches a false claim about an absent one.",
            category="verification",
            check=_post_condition_verification_is_independent,
        ),
        EvalTask(
            id="agent_recovers_or_stops_within_budget",
            description="The agent loop recovers from a single failed step but stops honestly within the failure budget when steps keep failing.",
            category="reliability",
            check=_agent_recovers_or_stops_within_budget,
        ),
    ]
