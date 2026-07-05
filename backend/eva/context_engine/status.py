from __future__ import annotations

from .models import ContextEngineStatus


def get_context_engine_status() -> ContextEngineStatus:
    return ContextEngineStatus(
        status="available",
        mode="local/mock preview only",
        live_llm_calls_enabled=False,
        provider_sdks_enabled=False,
        tool_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        secret_config_session_reads_enabled=False,
        next_phase="Phase 17 LLM Threat Defense + Prompt Injection Guard",
    )
