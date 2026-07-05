from __future__ import annotations

from .models import BrowserAgentStatus
from .policy import ALLOWED_STATUS_ACTIONS, BLOCKED_BROWSER_ACTIONS


def get_browser_agent_status() -> BrowserAgentStatus:
    return BrowserAgentStatus(
        phase="Phase 13F Browser Read-Only Readiness Proof",
        status="safety/readiness proof only",
        execution_enabled=False,
        real_browser_control="locked",
        allowed_now=ALLOWED_STATUS_ACTIONS,
        blocked_now=BLOCKED_BROWSER_ACTIONS,
        next_phase="Future BrowserAgent read-only gate with explicit policy, observation, verification, and audit gates",
        summary="BrowserAgent exists as a safety/status/readiness-proof foundation only. It does not launch, navigate, click, type, submit, read sessions, observe pages, or automate pages.",
    )
