from __future__ import annotations

from typing import Any

from .state import EvaRuntimeState


def _safety_line(state: EvaRuntimeState) -> str:
    if not state.safety_findings:
        return "Allowed. No guardrail finding was produced."
    finding = state.safety_findings[-1]
    warnings = finding.get("warnings") or []
    if finding.get("blocked"):
        reason = finding.get("reason") or "Blocked by guardrails."
        return f"Blocked. {reason}"
    if warnings:
        return "Warnings: " + ", ".join(str(item) for item in warnings)
    decision = (state.permission_decision or {}).get("decision")
    if decision == "ask_confirmation":
        return "Confirmation required before any external-visible action."
    if decision == "ask_override":
        return "Override required before any destructive or privacy-sensitive action."
    return "Allowed as a preview. Existing safety gates remain authoritative."


def _plan_lines(state: EvaRuntimeState) -> list[str]:
    if not state.proposed_actions:
        return ["No executable action was proposed."]
    lines: list[str] = []
    for index, action in enumerate(state.proposed_actions, start=1):
        summary = action.get("summary") or action.get("action_type") or action.get("delegate_to") or "Proposed action"
        suffix = ""
        decision = action.get("decision")
        if decision:
            suffix = f" ({decision})"
        lines.append(f"{index}. {summary}{suffix}")
    return lines


def _resource_hint_lines(state: EvaRuntimeState) -> list[str]:
    text = f"{state.normalized_intent or ''} {state.user_request or ''}".lower()
    hints: list[str] = []

    if "github" in text and "mcp" in text:
        hints.append(
            "github-mcp-server is experimental and disabled by default. Repo write, PR, merge, and delete actions require confirmation or override."
        )
    elif "mcp" in text:
        hints.append("MCP resources are cataloged for planning, but no MCP server is enabled or run by default.")

    if "chatgpt" in text and "chrome" in text:
        hints.append(
            "eva-chrome-execution-skills is the existing bounded Chrome path; playwright-python is experimental and disabled by default."
        )
    elif "chrome" in text or "browser" in text:
        hints.append("Browser resources require visible user-commanded actions and cannot read cookies, tokens, passwords, or storage.")

    if "spotify" in text:
        hints.append("eva-spotify-desktop-skill is the existing desktop-only Spotify path; no Spotify API, OAuth, or web player is implied.")

    if "pyautogui" in text:
        hints.append("pyautogui is experimental and disabled by default; desktop clicks require a high-confidence UiTarget.")

    if not hints:
        return []
    return ["", "Resource hint:", *hints]


def _relevant_research_memory_lines(state: EvaRuntimeState) -> list[str]:
    if not state.relevant_memory:
        return []
    try:
        from ..research_memory.context import format_research_context_for_state

        formatted = format_research_context_for_state(state.relevant_memory)
    except Exception:
        formatted = ""
    if not formatted:
        return []
    return ["", *formatted.splitlines()]


def _header(kind: str) -> list[str]:
    return [
        f"Eva v2 {kind} preview",
        "",
        "Normal chat routing:",
        "Disabled. This was an explicit v2 preview command.",
        "",
    ]


def _execute_safety_line(state: EvaRuntimeState) -> str:
    if state.execution_refused_reason:
        return state.execution_refused_reason
    decision = (state.permission_decision or {}).get("reason")
    if decision:
        return str(decision)
    return "Allowed low-risk action through the v2 safe execution bridge."


def format_v2_route_response(state: EvaRuntimeState) -> str:
    lines = _header("route")
    lines.extend(
        [
            "Intent:",
            state.normalized_intent or state.user_request,
            "",
            "Selected agent:",
            f"{(state.selected_agent or 'unknown').title()}Agent",
            "",
            "Reason:",
            state.route_reason or "Selected by deterministic capability scores.",
            "",
            "Safety:",
            _safety_line(state),
        ]
    )
    lines.extend(_relevant_research_memory_lines(state))
    lines.extend(["", "No action was executed."])
    return "\n".join(lines)


def format_v2_execute_response(state: EvaRuntimeState) -> str:
    if state.pending_action:
        return _format_pending_execute_response(state)
    refused = bool(state.execution_refused_reason)
    lines = [
        "Eva v2 execution refused" if refused else "Eva v2 execution result",
        "",
        "Normal chat routing:",
        "Disabled. This was an explicit v2 execution command.",
        "",
        "Intent:",
        state.normalized_intent or state.user_request,
        "",
        "Selected agent:",
        f"{(state.selected_agent or 'unknown').title()}Agent",
        "",
        "Safety:",
        _execute_safety_line(state),
        "",
        "Execution:",
    ]
    if refused:
        lines.extend(
            [
                "Refused by v2 read-only policy or the existing safety gates.",
                "",
                "No real action was executed.",
                "",
                "Trace:",
                state.trace_id or "not written",
            ]
        )
        return "\n".join(lines)

    executed_by = state.executed_by or "existing Eva safe handler"
    if executed_by == "existing_eva_status_command_handler":
        execution_line = "Executed through existing Eva status command handler."
    elif executed_by == "eva-chrome-execution-skills":
        execution_line = "Executed through existing Eva Chrome Execution Skills."
    elif executed_by.startswith("v2_read_only_delegate:"):
        execution_line = "Executed through v2 read-only delegate."
    else:
        execution_line = f"Executed through {executed_by}."
    lines.append(execution_line)
    lines.extend(_relevant_research_memory_lines(state))
    lines.extend(
        [
            "",
            "Result:",
            state.execution_summary or "The allowlisted action completed without a detailed summary.",
            "",
            "Trace:",
            state.trace_id or "not written",
        ]
    )
    return "\n".join(lines)


def _format_pending_execute_response(state: EvaRuntimeState) -> str:
    action = state.pending_action or {}
    status = str(action.get("status") or "")
    risk = str(action.get("risk_category") or "unknown")
    summary = str(action.get("summary") or "Permission-gated action")
    action_id = str(action.get("id") or "unknown")
    action_type = str(action.get("action_type") or state.normalized_intent or state.user_request)
    requires_override = bool(action.get("requires_override"))

    if status == "refused":
        return "\n".join(
            [
                "Eva v2 execution refused",
                "",
                "Normal chat routing:",
                "Disabled. This was an explicit v2 execution command.",
                "",
                "Intent:",
                state.normalized_intent or state.user_request,
                "",
                "Safety:",
                state.execution_refused_reason or str(action.get("safety_reason") or "Execution is disabled for this action."),
                "",
                "Execution:",
                "Refused by v2 read-only policy or the existing safety gates.",
                "",
                "No real action was executed.",
                "",
                "Trace:",
                state.trace_id or "not written",
            ]
        )

    header = "Eva v2 execution requires override" if requires_override else "Eva v2 execution requires confirmation"
    next_line = (
        f"Say `confirm override {action_id}` only if you understand this is destructive."
        if requires_override
        else f"Say `confirm {action_id}` to approve this exact action."
    )
    unavailable = _executor_unavailable_note(action)
    lines = [
        header,
        "",
        "Normal chat routing:",
        "Disabled. This was an explicit v2 execution command.",
        "",
        "Intent:",
        action_type,
        "",
        "Pending action:",
        f"ID: {action_id}",
        f"Status: {status}",
        f"Risk: {risk}",
        f"Summary: {summary}",
        "",
        "Execution:",
        "No real action was executed.",
        "",
        "Next:",
        next_line,
    ]
    if unavailable:
        lines.append(unavailable)
    lines.extend(["", "Trace:", state.trace_id or "not written"])
    return "\n".join(lines)


def _executor_unavailable_note(action: dict[str, Any]) -> str:
    if action.get("executor_available"):
        return ""
    category = str(action.get("risk_category") or "")
    if category == "external_message":
        return "This build still cannot automatically send WhatsApp until a later verified executor phase."
    if category == "destructive_file_action":
        return "This build still cannot delete files through v2 until a later verified executor phase."
    if category == "desktop_control":
        return "This build still cannot run desktop clicks or typing through v2 until a later verified executor phase."
    return "This build does not yet have a verified executor for this action."


def format_v2_plan_response(state: EvaRuntimeState) -> str:
    lines = _header("plan")
    lines.extend(
        [
            "Intent:",
            state.normalized_intent or state.user_request,
            "",
            "Selected agent:",
            f"{(state.selected_agent or 'unknown').title()}Agent",
            "",
            "Safety:",
            _safety_line(state),
            "",
            "Proposed plan:",
        ]
    )
    lines.extend(_plan_lines(state))
    lines.extend(_relevant_research_memory_lines(state))
    lines.extend(_resource_hint_lines(state))
    lines.extend(["", "No action was executed."])
    return "\n".join(lines)


def format_v2_dry_run_response(state: EvaRuntimeState) -> str:
    lines = _header("dry run")
    lines.extend(
        [
            "Intent:",
            state.normalized_intent or state.user_request,
            "",
            "Selected agent:",
            f"{(state.selected_agent or 'unknown').title()}Agent",
            "",
            "Safety:",
            _safety_line(state),
            "",
            "Proposed plan:",
        ]
    )
    lines.extend(_plan_lines(state))
    lines.extend(_relevant_research_memory_lines(state))
    lines.extend(_resource_hint_lines(state))
    lines.extend(
        [
            "",
            "Execution:",
            state.skipped_execution_reason
            or "Skipped because this was dry-run mode.",
            "",
            "Delegation target:",
            _delegation_target(state),
            "",
            "Trace:",
            state.trace_id or "not written",
            "",
            "Result:",
            "No real action was executed.",
        ]
    )
    return "\n".join(lines)


def _delegation_target(state: EvaRuntimeState) -> str:
    for action in state.proposed_actions:
        target = action.get("delegate_to")
        if target:
            return str(target)
    return "Existing Eva capability router / permission gate."


def format_v2_response(state: EvaRuntimeState, mode: str) -> str:
    if mode in {"execute", "run"}:
        return format_v2_execute_response(state)
    if mode == "route":
        return format_v2_route_response(state)
    if mode == "plan":
        return format_v2_plan_response(state)
    return format_v2_dry_run_response(state)
