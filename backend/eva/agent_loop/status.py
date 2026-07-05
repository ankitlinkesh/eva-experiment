from __future__ import annotations

from .models import AgentLoopStatus


def get_agent_loop_status() -> AgentLoopStatus:
    return AgentLoopStatus(
        status="available",
        mode="local/mock preview only",
        live_llm_calls_enabled=False,
        provider_sdks_enabled=False,
        tool_execution_enabled=False,
        browser_desktop_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        secret_config_session_reads_enabled=False,
        new_write_paths_enabled=False,
        next_phase="Phase 19 Agentic Workflow Planner",
    )
