from __future__ import annotations

from .finalizer import final_summary_lines
from .models import AgentLoopState


def format_agent_loop_report(state: AgentLoopState) -> str:
    lines = [
        "Agent Loop v1 preview report",
        "Agent loop is local/mock preview only.",
        "No live LLM call was made.",
        "Actions are preview-only.",
        "Tools are not executed.",
        "Secrets/config/session data are blocked.",
        "Browser/desktop/shell/cloud/MCP execution remains locked.",
        "",
        f"Loop ID: {state.loop_id}",
        f"Request summary: {state.request_summary}",
        f"Current stage: {state.current_stage}",
        f"Steps used: {state.step_count}/{state.max_step_limit}",
        f"Selected capabilities: {_join(state.selected_capabilities)}",
        f"Context packet summary: {state.context_packet_summary}",
        f"Threat scan summary: {state.threat_scan_summary}",
        "",
        "Planned preview steps:",
    ]
    lines.extend(f"- {item}" for item in state.planned_preview_steps)
    lines.append("")
    lines.append("Action previews:")
    for item in state.action_previews:
        reason = f"; blocked reason: {item.blocked_reason}" if item.blocked_reason else ""
        lines.append(
            f"- {item.action_id}: {item.action_type}; capability: {item.capability_requested}; "
            f"risk: {item.risk_level}; status: {item.execution_status}; {item.no_action_executed_statement}{reason}"
        )
    lines.append("")
    lines.append("Mock observations:")
    lines.extend(f"- {item.observation_id}: {item.summary}; execution used: {item.execution_used}" for item in state.mock_observations)
    lines.append("")
    lines.append("Verification notes:")
    lines.extend(f"- {item.check_id}: {item.status} - {item.summary}" for item in state.verification_notes)
    if state.blocked_actions:
        lines.append("")
        lines.append("Blocked actions:")
        lines.extend(f"- {item.action_id}: {item.blocked_reason}" for item in state.blocked_actions)
    lines.append("")
    lines.extend(final_summary_lines(state))
    return "\n".join(lines)


def _join(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else "none"
