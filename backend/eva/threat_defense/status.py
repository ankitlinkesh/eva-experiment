from __future__ import annotations

from .models import ThreatDefenseStatus


def get_threat_defense_status() -> ThreatDefenseStatus:
    return ThreatDefenseStatus(
        status="available",
        mode="local/mock preview only",
        live_llm_calls_enabled=False,
        provider_sdks_enabled=False,
        tool_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        secret_config_session_reads_enabled=False,
        next_phase="Phase 18 Agent Loop v1",
    )
