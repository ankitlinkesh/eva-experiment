from __future__ import annotations

from typing import Any

from ..browser.web_apps import resolve_web_app
from ..permissions.confirmation import create_pending_action_from_state
from .execution_policy import (
    browser_app_from_state,
    evaluate_v2_execution_allowed,
    is_allowlisted_code_readonly_action,
    is_allowlisted_memory_readonly_action,
    is_allowlisted_research_readonly_action,
    is_low_risk_status_action,
)
from .read_only_delegates import execute_code_readonly_delegate, execute_memory_readonly_delegate, execute_research_readonly_delegate
from .state import EvaRuntimeState


def execute_v2_allowlisted_action(state: EvaRuntimeState) -> EvaRuntimeState:
    decision = evaluate_v2_execution_allowed(state)
    state.permission_decision = decision.as_dict()
    if decision.decision != "allow":
        state.execution_allowed = False
        state.execution_refused_reason = decision.reason
        pending_action = _maybe_create_pending_action(state, decision.reason)
        if pending_action:
            state.pending_action = pending_action.as_dict()
            state.observations.append(
                {
                    "source": "v2_execute",
                    "summary": f"Pending action {pending_action.id} recorded with status {pending_action.status}. No real action was executed.",
                    "pending_action_id": pending_action.id,
                    "pending_action_status": pending_action.status,
                }
            )
        else:
            state.observations.append({"source": "v2_execute", "summary": f"Execution refused: {decision.reason}"})
        state.touch()
        return state

    state.execution_allowed = True
    state.execution_refused_reason = None
    if is_low_risk_status_action(state):
        result = _run_status_action(state)
        state.executed_by = "existing_eva_status_command_handler"
        state.execution_summary = result
        state.executed_actions.append(
            {
                "action_type": "status.read_only",
                "status": "executed",
                "executed_by": state.executed_by,
                "summary": "Executed through existing Eva status command handler.",
            }
        )
        state.observations.append({"source": "v2_execute", "summary": "Read-only status command executed."})
        state.touch()
        return state

    app_key = browser_app_from_state(state)
    if app_key:
        result = _run_browser_open_action(app_key)
        ok = bool(result.get("ok")) if isinstance(result, dict) else False
        message = _clean_result_message(result, fallback=f"Requested Chrome open for {app_key}.")
        state.executed_by = "eva-chrome-execution-skills"
        state.execution_summary = message
        state.executed_actions.append(
            {
                "action_type": "browser.open_public_webapp",
                "status": "executed" if ok else "attempted_unverified",
                "executed_by": state.executed_by,
                "target": app_key,
                "summary": message,
            }
        )
        state.observations.append({"source": "v2_execute", "summary": message, "ok": ok})
        state.touch()
        return state

    if is_allowlisted_code_readonly_action(state):
        return _run_readonly_delegate(state, "code", execute_code_readonly_delegate)

    if is_allowlisted_research_readonly_action(state):
        return _run_readonly_delegate(state, "research", execute_research_readonly_delegate)

    if is_allowlisted_memory_readonly_action(state):
        return _run_readonly_delegate(state, "memory", execute_memory_readonly_delegate)

    state.execution_allowed = False
    state.execution_refused_reason = "V2 execution bridge refused this action. Use v2 dry run/plan, or wait for a later permission-gated phase."
    state.observations.append({"source": "v2_execute", "summary": f"Execution refused: {state.execution_refused_reason}"})
    state.touch()
    return state


def _run_readonly_delegate(state: EvaRuntimeState, agent_name: str, handler: Any) -> EvaRuntimeState:
    ok, summary = handler(state)
    state.executed_by = f"v2_read_only_delegate:{agent_name}"
    state.execution_summary = _safe_summary(summary)
    if not ok:
        state.execution_allowed = False
        state.execution_refused_reason = state.execution_summary
    state.executed_actions.append(
        {
            "action_type": _first_action_type(state),
            "status": "executed" if ok else "unavailable",
            "executed_by": state.executed_by,
            "read_only": True,
            "summary": state.execution_summary,
        }
    )
    state.observations.append({"source": "v2_execute", "summary": state.execution_summary, "ok": bool(ok), "read_only": True})
    state.touch()
    return state


def _run_status_action(state: EvaRuntimeState) -> str:
    text = " ".join(str(state.normalized_intent or state.user_request or "").lower().strip().split())
    if text in {"resources status", "resource registry status"}:
        from ..resources.status import format_resource_registry_status

        return format_resource_registry_status()
    if text in {"mcp status", "mcp policy status"}:
        from ..resources.status import format_mcp_policy_status

        return format_mcp_policy_status()
    if text in {"open source tools status", "open-source tools status"}:
        from ..resources.status import format_open_source_tools_status

        return format_open_source_tools_status()
    if text.startswith("resource detail ") or text.startswith("tool resource detail "):
        from ..resources.status import format_resource_detail

        resource_id = text.removeprefix("tool resource detail ").removeprefix("resource detail ").strip()
        return format_resource_detail(resource_id)
    if text in {"agents status"}:
        from .supervisor import supervisor_status

        status = supervisor_status()
        agents = status.get("agents") if isinstance(status.get("agents"), list) else []
        lines = [f"Specialist agents status: {len(agents)} v2 skeleton agents are registered."]
        for item in agents:
            if isinstance(item, dict):
                lines.append(f"- {item.get('name')}: {item.get('delegated_core')}")
        return "\n".join(lines)
    if text in {"guardrails status"}:
        from ..guardrails.llm_guard_adapter import is_llm_guard_available

        return f"Guardrails status: LLM Guard package is {'available' if is_llm_guard_available() else 'not installed'}; fallback guardrails remain active."
    if text in {"vector memory status"}:
        from ..vector_memory.retriever import vector_memory_status

        status = vector_memory_status()
        return f"Vector memory status: interfaces installed, primary backend is {status.get('primary')}; enabled={status.get('enabled')}."
    if text in {"traces status"}:
        from ..observability.traces import traces_status

        status = traces_status()
        return f"Traces status: local trace store is {status.get('backend')} at {status.get('path')}."
    if text in {"eva v2 status"}:
        from .feature_flags import eva_v2_runtime_status

        status = eva_v2_runtime_status()
        return f"Eva v2 runtime status: {'enabled' if status.get('enabled') else 'installed but disabled'}. Normal chat routing remains unchanged."
    return "Status command is not available through the v2 execution bridge."


def _run_browser_open_action(app_key: str) -> dict[str, Any]:
    resolved = resolve_web_app(app_key)
    if not resolved:
        return {"ok": False, "message": f"I could not resolve {app_key} as an allowlisted web app."}
    from ..browser import skills as browser_skills

    return browser_skills.chrome_open_web_app(str(resolved["key"]))


def _clean_result_message(result: Any, *, fallback: str) -> str:
    if isinstance(result, dict):
        message = str(result.get("message") or "").strip()
        if message:
            return message
        if result.get("ok"):
            app = str(result.get("app") or "the web app")
            return f"Done, {app} is open in Chrome."
        error = str(result.get("error") or "").strip()
        if error:
            return f"Chrome open action was unavailable: {error}."
    return fallback


def _first_action_type(state: EvaRuntimeState) -> str:
    for action in state.proposed_actions:
        if isinstance(action, dict) and action.get("action_type"):
            return str(action["action_type"])
    return "read_only.unknown"


def _safe_summary(summary: str) -> str:
    text = str(summary or "").strip()
    return text[:6000] if text else "Read-only delegate completed without a detailed summary."


def _maybe_create_pending_action(state: EvaRuntimeState, reason: str):
    text = " ".join(str(state.normalized_intent or state.user_request or "").lower().split())
    if state.safety_findings and state.safety_findings[-1].get("blocked"):
        return None
    if "delete memory" in text or "forget memory" in text:
        return None
    if "pyautogui" in text:
        return None
    pending_markers = (
        "send whatsapp",
        "whatsapp message",
        "send message",
        "delete",
        "click ",
        "type ",
        "button",
        "screen",
        "desktop",
        "mcp",
        "model context protocol",
        "playwright",
    )
    if not any(marker in text for marker in pending_markers):
        return None
    action = create_pending_action_from_state(state, reason=reason)
    if state.trace_id:
        from ..observability.traces import log_pending_action_event

        log_pending_action_event(
            state.trace_id,
            "pending_action_created",
            {
                "action_id": action.id,
                "risk_category": action.risk_category,
                "status": action.status,
                "summary": action.summary,
                "source": action.source,
                "selected_agent": action.selected_agent,
            },
        )
    return action
