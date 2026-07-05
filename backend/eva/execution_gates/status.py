from __future__ import annotations

from .models import ExecutionGateStatus


def get_execution_gates_status() -> ExecutionGateStatus:
    return ExecutionGateStatus(
        status="available",
        mode="local/mock policy preview only",
        live_llm_calls_enabled=False,
        provider_sdks_enabled=False,
        tool_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        arbitrary_file_writes_enabled=False,
        secret_config_session_reads_enabled=False,
        browser_desktop_shell_cloud_mcp_execution_enabled=False,
        new_write_paths_enabled=False,
        existing_real_write_boundary="Phase 12L narrow approved new .md/.txt real-create gate only",
        next_phase="Phase 21 Memory v3",
    )
