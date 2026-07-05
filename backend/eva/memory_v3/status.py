from __future__ import annotations

from .models import MemoryV3Status


def get_memory_v3_status() -> MemoryV3Status:
    return MemoryV3Status(
        status="available",
        mode="local-only policy/status/preview",
        local_only=True,
        live_llm_calls_enabled=False,
        provider_sdks_enabled=False,
        cloud_memory_enabled=False,
        remote_sync_enabled=False,
        tool_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        arbitrary_file_writes_enabled=False,
        raw_memory_db_dumps_enabled=False,
        secret_config_session_reads_enabled=False,
        next_phase="Phase 22 Voice Assistant",
    )
