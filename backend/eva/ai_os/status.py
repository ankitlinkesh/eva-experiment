from __future__ import annotations

from .models import AIOSStatus


def get_ai_os_status() -> AIOSStatus:
    return AIOSStatus(
        status="available",
        mode="local/status only",
        current_phase="Phase 26 Real Desktop Control Gate",
        overall_readiness="local/mock desktop-control gate reports ready; real desktop control locked",
        live_llm_calls_enabled=False,
        provider_sdks_enabled=False,
        tool_execution_enabled=False,
        web_server_enabled=False,
        browser_launch_enabled=False,
        desktop_ui_enabled=False,
        background_daemon_enabled=False,
        arbitrary_file_reads_enabled=False,
        arbitrary_file_writes_enabled=False,
        next_phase="Phase 27 News/Web Intelligence Dashboard",
    )
