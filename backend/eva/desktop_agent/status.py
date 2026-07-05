from __future__ import annotations

from .models import DesktopAgentStatus
from .policy import ALLOWED_DESKTOP_STATUS_ACTIONS, BLOCKED_DESKTOP_ACTIONS


def get_desktop_agent_status() -> DesktopAgentStatus:
    return DesktopAgentStatus(
        phase="Phase 14A-14G DesktopAgent Locked Safety Foundation",
        status="safety/status only",
        execution_enabled=False,
        real_screen_observation="locked",
        real_desktop_control="locked",
        allowed_now=ALLOWED_DESKTOP_STATUS_ACTIONS,
        blocked_now=BLOCKED_DESKTOP_ACTIONS,
        next_phase="Phase 15 LLM Router + Structured Reasoning Core",
        summary="DesktopAgent exists as a safety/status, session-preview, and screen-observation-policy foundation only. It does not capture screens, take screenshots, run OCR or image analysis, inspect real windows/apps, detect active apps, launch apps, move/click/type, use hotkeys, use clipboard, automate file dialogs, or run terminal/package/cloud actions.",
    )
