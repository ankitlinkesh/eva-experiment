from __future__ import annotations

from typing import Any

from ..agents.supervisor_agent import select_agent_for_intent
from ..guardrails.llm_guard_adapter import guard_input
from ..observability.traces import end_trace, log_agent_selection, log_verification, start_trace
from ..schemas.results import EvaVerificationResult
from .feature_flags import get_v2_feature_flags
from .state import EvaRuntimeState


def load_context_node(state: EvaRuntimeState, context: dict[str, Any] | None = None) -> EvaRuntimeState:
    state.task_context = dict((context or {}).get("task_context", {}))
    state.touch()
    return state


def classify_intent_node(state: EvaRuntimeState) -> EvaRuntimeState:
    state.normalized_intent = " ".join(state.user_request.lower().strip().split())
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
    agent = select_agent_for_intent(state.normalized_intent or state.user_request, state)
    state.selected_agent = agent.name
    if state.trace_id:
        log_agent_selection(state.trace_id, agent.name, "highest capability score")
    state.touch()
    return state


def plan_node(state: EvaRuntimeState) -> EvaRuntimeState:
    agent = select_agent_for_intent(state.normalized_intent or state.user_request, state)
    result = agent.plan(state)
    state.proposed_actions.extend(result.proposed_actions)
    state.final_response = result.message
    state.touch()
    return state


def permission_node(state: EvaRuntimeState) -> EvaRuntimeState:
    state.permission_decision = {"decision": "delegate", "reason": "Phase 1 does not execute risky actions directly."}
    state.touch()
    return state


def execute_node(state: EvaRuntimeState) -> EvaRuntimeState:
    flags = get_v2_feature_flags()
    if not flags.runtime_enabled:
        state.executed_actions.append({"delegated": True, "reason": "v2 runtime disabled; active Eva loop remains primary"})
    state.touch()
    return state


def observe_node(state: EvaRuntimeState) -> EvaRuntimeState:
    state.observations.append({"source": "v2_skeleton", "summary": "No direct risky action executed in Phase 1."})
    state.touch()
    return state


def verify_node(state: EvaRuntimeState) -> EvaRuntimeState:
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
