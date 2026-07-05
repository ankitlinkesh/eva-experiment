from __future__ import annotations

from .models import AgentLoopState


def final_status_for_state(blocked: bool, stop_reason: str) -> str:
    if stop_reason in {"step_limit_exceeded", "repeated_step_detected", "no_progress_detected"}:
        return "safe_stopped_preview"
    if blocked:
        return "refusal_preview"
    return "completed_preview"


def final_summary_lines(state: AgentLoopState) -> tuple[str, ...]:
    return (
        f"Final status: {state.final_status}.",
        f"Stop reason: {state.stop_reason}.",
        state.no_live_llm_call_statement,
        state.no_tool_execution_statement,
        "Agent loop is local/mock preview only.",
        "Actions are preview-only.",
        "Tools are not executed.",
        "Secrets/config/session data are blocked.",
        "Browser/desktop/shell/cloud/MCP execution remains locked.",
    )
