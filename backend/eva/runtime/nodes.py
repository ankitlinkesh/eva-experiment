from __future__ import annotations

from typing import Any

from ..agents.supervisor_agent import select_agent_for_intent, select_agent_with_reason
from ..guardrails.llm_guard_adapter import guard_input
from ..observability.traces import end_trace, log_agent_selection, log_dry_run_preview, log_execution_bridge, log_verification, start_trace
from ..runtime.formatters import format_v2_dry_run_response
from ..schemas.results import EvaVerificationResult
from .execution_bridge import execute_v2_allowlisted_action
from .execution_policy import evaluate_v2_execution_allowed
from .feature_flags import get_v2_feature_flags
from .state import EvaRuntimeState


def load_context_node(state: EvaRuntimeState, context: dict[str, Any] | None = None) -> EvaRuntimeState:
    state.task_context = dict((context or {}).get("task_context", {}))
    state.touch()
    return state


def classify_intent_node(state: EvaRuntimeState) -> EvaRuntimeState:
    state.normalized_intent = _normalize_intent(state.user_request)
    state.touch()
    return state


def retrieve_memory_node(state: EvaRuntimeState) -> EvaRuntimeState:
    state.relevant_memory = []
    state.touch()
    return state


def safety_precheck_node(state: EvaRuntimeState) -> EvaRuntimeState:
    finding = guard_input(state.user_request)
    state.safety_findings.append(finding.as_dict())
    state.touch()
    return state


def route_agent_node(state: EvaRuntimeState) -> EvaRuntimeState:
    selection = select_agent_with_reason(state.normalized_intent or state.user_request, state)
    agent = selection.agent
    state.selected_agent = agent.name
    state.route_score = selection.score
    state.route_reason = selection.reason
    if state.trace_id:
        log_agent_selection(state.trace_id, agent.name, selection.reason)
    state.touch()
    return state


def plan_node(state: EvaRuntimeState) -> EvaRuntimeState:
    agent = select_agent_for_intent(state.normalized_intent or state.user_request, state)
    result = agent.plan(state)
    state.proposed_actions.extend(result.proposed_actions)
    state.plan_summary = result.message
    state.final_response = result.message
    state.touch()
    return state


def permission_node(state: EvaRuntimeState) -> EvaRuntimeState:
    if state.safety_findings and state.safety_findings[-1].get("blocked"):
        state.permission_decision = {"decision": "hard_block", "reason": state.safety_findings[-1].get("reason") or "Blocked by guardrails."}
        state.touch()
        return state
    decisions = {str(action.get("decision") or "") for action in state.proposed_actions}
    if "blocked" in decisions:
        state.permission_decision = {"decision": "hard_block", "reason": "Blocked by SafetyAgent preview."}
    elif "override_required" in decisions:
        state.permission_decision = {"decision": "ask_override", "reason": "Override required before destructive or system-changing action.", "required_phrase": "confirm override"}
    elif "confirmation_required" in decisions:
        state.permission_decision = {"decision": "ask_confirmation", "reason": "Confirmation required before external-visible action."}
    else:
        state.permission_decision = {"decision": "delegate", "reason": "Phase 2 preview does not execute actions directly."}
    state.touch()
    return state


def execute_node(state: EvaRuntimeState) -> EvaRuntimeState:
    flags = get_v2_feature_flags()
    if not flags.runtime_enabled:
        state.executed_actions.append({"delegated": True, "reason": "v2 runtime disabled; active Eva loop remains primary"})
    state.touch()
    return state


def dry_run_execute_node(state: EvaRuntimeState) -> EvaRuntimeState:
    state.dry_run = True
    state.execution_mode = "dry_run"
    state.provenance = "v2_dry_run"
    state.skipped_execution_reason = "Dry run mode: no browser, desktop, message, file deletion, form submission, or external side effect was executed."
    if not state.proposed_actions:
        state.observations.append({"source": "v2_dry_run", "summary": "No executable action was proposed."})
    for action in state.proposed_actions:
        preview = dict(action)
        preview["status"] = "skipped_dry_run"
        state.executed_actions.append(preview)
    state.observations.append({"source": "v2_dry_run", "summary": "Plan preview generated. No action executed."})
    state.verification_results.append(
        {
            "action_id": state.task_id,
            "verified": True,
            "confidence": 0.78,
            "evidence": "Plan safety preview generated; no real-world completion was claimed.",
            "failure_reason": None,
            "suggested_repair": None,
            "source": "v2_dry_run",
            "mode": "dry_run",
            "message": "Plan preview generated. No action executed.",
        }
    )
    if state.trace_id:
        log_dry_run_preview(
            state.trace_id,
            {
                "request_id": state.request_id,
                "command_type": "dry_run",
                "user_request": state.user_request,
                "selected_agent": state.selected_agent,
                "safety_summary": state.permission_decision,
                "proposed_action_summaries": [action.get("summary") for action in state.proposed_actions],
                "skipped_execution_reason": state.skipped_execution_reason,
            },
        )
    state.touch()
    return state


def safe_execute_node(state: EvaRuntimeState) -> EvaRuntimeState:
    state.dry_run = False
    state.execution_mode = "v2_execute"
    state.provenance = "v2_execute"
    state = execute_v2_allowlisted_action(state)
    if state.trace_id:
        log_execution_bridge(
            state.trace_id,
            {
                "command_type": "v2_execute",
                "request_id": state.request_id,
                "selected_agent": state.selected_agent,
                "proposed_actions": state.proposed_actions,
                "execution_allowed": state.execution_allowed,
                "execution_refused_reason": state.execution_refused_reason,
                "executed_by": state.executed_by,
                "pending_action": state.pending_action,
                "read_only": bool(state.executed_by and state.executed_by.startswith("v2_read_only_delegate:")),
                "result_summary": state.execution_summary,
            },
        )
    state.touch()
    return state


def observe_node(state: EvaRuntimeState) -> EvaRuntimeState:
    if state.execution_mode == "v2_execute":
        state.touch()
        return state
    state.observations.append({"source": "v2_skeleton", "summary": "No direct risky action executed in Phase 1."})
    state.touch()
    return state


def verify_node(state: EvaRuntimeState) -> EvaRuntimeState:
    if state.dry_run:
        state.touch()
        return state
    if state.execution_mode == "v2_execute":
        if state.execution_refused_reason:
            result = EvaVerificationResult(
                action_id=state.task_id,
                verified=True,
                confidence=0.9,
                evidence="Execution was safely refused before any tool ran.",
                source="v2_execute",
            )
        elif state.execution_summary:
            result = EvaVerificationResult(
                action_id=state.task_id,
                verified=True,
                confidence=0.76,
                evidence="Allowlisted execution produced a clean result summary.",
                source="v2_execute",
            )
        else:
            result = EvaVerificationResult(
                action_id=state.task_id,
                verified=False,
                confidence=0.2,
                evidence="Execution bridge did not produce a result summary.",
                failure_reason="missing_execution_summary",
                suggested_repair="Use v2 dry run or retry after bridge support is expanded.",
                source="v2_execute",
            )
        state.verification_results.append(result.as_dict())
        if state.trace_id:
            log_verification(state.trace_id, result.as_dict())
        state.touch()
        return state
    result = EvaVerificationResult(
        action_id=state.task_id,
        verified=True,
        confidence=0.72,
        evidence="v2 skeleton produced typed state and delegated execution safely.",
        source="v2_skeleton",
    )
    state.verification_results.append(result.as_dict())
    if state.trace_id:
        log_verification(state.trace_id, result.as_dict())
    state.touch()
    return state


def repair_or_rollback_node(state: EvaRuntimeState) -> EvaRuntimeState:
    state.touch()
    return state


def final_response_node(state: EvaRuntimeState) -> EvaRuntimeState:
    if state.dry_run:
        state.final_response = format_v2_dry_run_response(state)
        if state.trace_id:
            end_trace(state.trace_id, state.final_response)
        state.touch()
        return state
    if state.execution_mode == "v2_execute":
        from .formatters import format_v2_execute_response

        state.final_response = format_v2_execute_response(state)
        if state.trace_id:
            end_trace(state.trace_id, state.final_response)
        state.touch()
        return state
    if not state.final_response:
        state.final_response = "Eva v2 runtime skeleton handled this as a safe delegated request."
    if state.trace_id:
        end_trace(state.trace_id, state.final_response)
    state.touch()
    return state


def run_fallback_nodes(user_request: str, context: dict[str, Any] | None = None) -> EvaRuntimeState:
    state = EvaRuntimeState(user_request=user_request)
    state.trace_id = start_trace(state.request_id, user_request)
    for node in (
        load_context_node,
        classify_intent_node,
        retrieve_memory_node,
        safety_precheck_node,
        route_agent_node,
        plan_node,
        permission_node,
        execute_node,
        observe_node,
        verify_node,
        repair_or_rollback_node,
        final_response_node,
    ):
        state = node(state, context) if node is load_context_node else node(state)
    return state


def run_preview_nodes(user_request: str, *, mode: str, context: dict[str, Any] | None = None) -> EvaRuntimeState:
    state = EvaRuntimeState(user_request=user_request)
    state.dry_run = mode == "dry_run"
    state.execution_mode = "dry_run" if mode in {"dry_run", "plan", "route"} else "normal"
    state.provenance = "v2_dry_run" if mode == "dry_run" else "v2_preview"
    state.trace_id = start_trace(state.request_id, user_request) if mode == "dry_run" else None
    nodes = [load_context_node, classify_intent_node, retrieve_memory_node, safety_precheck_node, route_agent_node]
    if mode in {"plan", "dry_run"}:
        nodes.extend([plan_node, permission_node])
    for node in nodes:
        state = node(state, context) if node is load_context_node else node(state)
    if mode == "route":
        from .formatters import format_v2_route_response

        state.final_response = format_v2_route_response(state)
        state.touch()
        return state
    if mode == "plan":
        from .formatters import format_v2_plan_response

        state.final_response = format_v2_plan_response(state)
        state.touch()
        return state
    state = dry_run_execute_node(state)
    state = final_response_node(state)
    return state


def run_execute_nodes(user_request: str, context: dict[str, Any] | None = None) -> EvaRuntimeState:
    state = EvaRuntimeState(user_request=user_request)
    state.execution_mode = "v2_execute"
    state.provenance = "v2_execute"
    state.trace_id = start_trace(state.request_id, user_request)
    for node in (
        load_context_node,
        classify_intent_node,
        retrieve_memory_node,
        safety_precheck_node,
        route_agent_node,
        plan_node,
        permission_node,
        safe_execute_node,
        observe_node,
        verify_node,
        repair_or_rollback_node,
        final_response_node,
    ):
        state = node(state, context) if node is load_context_node else node(state)
    return state


def _normalize_intent(user_request: str) -> str:
    text = " ".join(str(user_request or "").lower().strip().split())
    prefixes = ("eva v2 dry run ", "eva v2 plan ", "eva v2 route ", "eva v2 execute ", "eva v2 run ")
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return text
