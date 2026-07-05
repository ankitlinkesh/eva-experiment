from __future__ import annotations

from .models import BrowserSessionPolicy


ALLOWED_STATUS_ACTIONS = (
    "browser status",
    "browser policy summary",
    "action safety preview",
    "domain policy preview",
    "domain/site-risk preview",
    "read-only readiness proof",
    "locked feature explanation",
)


BLOCKED_BROWSER_ACTIONS = (
    "launching browser",
    "navigating real pages",
    "clicking",
    "typing",
    "submitting forms",
    "login automation",
    "payments",
    "file upload execution",
    "download execution",
    "cookie access",
    "localStorage access",
    "password/session/profile reads",
    "screenshots",
    "screen watching",
    "Playwright/browser-use/Stagehand/Maxun execution",
    "MCP",
    "PyAutoGUI",
    "shell/package/cloud calls",
)


def get_browser_session_policy() -> BrowserSessionPolicy:
    return BrowserSessionPolicy(
        real_browser_control_enabled=False,
        launch_browser_allowed=False,
        navigate_allowed=False,
        click_allowed=False,
        type_allowed=False,
        submit_allowed=False,
        screenshot_allowed=False,
        screen_watch_allowed=False,
        automation_backends_enabled=(),
        allowed_status_actions=ALLOWED_STATUS_ACTIONS,
    )


def browser_policy_summary() -> str:
    return "BrowserAgent is safety/readiness-proof only. Real browser control is locked; policy/readiness/action/domain previews are allowed."
