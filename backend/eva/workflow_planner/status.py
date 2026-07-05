from __future__ import annotations

from .models import WorkflowPlannerStatus


def get_workflow_planner_status() -> WorkflowPlannerStatus:
    return WorkflowPlannerStatus(
        status="available",
        mode="local/mock preview only",
        live_llm_calls_enabled=False,
        provider_sdks_enabled=False,
        tool_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        arbitrary_file_writes_enabled=False,
        secret_config_session_reads_enabled=False,
        browser_desktop_execution_enabled=False,
        next_phase="Phase 20 Controlled Execution Gates",
    )
