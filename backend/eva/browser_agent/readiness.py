from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserSessionReadiness:
    status: str
    ready_for_preview_records: bool
    ready_for_readonly_mode: bool
    ready_for_real_browser_control: bool
    allowed_now: tuple[str, ...]
    gaps: tuple[str, ...]
    next_phase: str
    summary: str


def get_browser_session_readiness() -> BrowserSessionReadiness:
    return BrowserSessionReadiness(
        status="preview only",
        ready_for_preview_records=True,
        ready_for_readonly_mode=False,
        ready_for_real_browser_control=False,
        allowed_now=(
            "browser session status previews",
            "preview-only session records",
            "future lifecycle plan",
            "readiness gap explanations",
        ),
        gaps=(
            "no real browser launch or navigation policy is enabled",
            "no page observation, DOM read, screenshot, or screen capture is enabled",
            "no click/type/submit/login/payment/upload/download gates are enabled",
            "no cookie, localStorage, profile, password, session, or token access is allowed",
            "no Playwright/browser-use/Stagehand/Maxun/MCP/PyAutoGUI execution is enabled",
            "no verification and repair loop exists for real browser actions yet",
        ),
        next_phase="BrowserAgent read-only status/preview with explicit observation policy, still without real control.",
        summary="Browser sessions are preview/status records only. Real browser control remains locked.",
    )
