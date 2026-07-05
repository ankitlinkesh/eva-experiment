from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


ALLOWED_SESSION_PREVIEW_ACTIONS: tuple[str, ...] = (
    "create preview-only browser session records",
    "list preview sessions",
    "show latest browser session preview",
    "show BrowserAgent readiness",
    "explain blocked browser actions",
    "show future session lifecycle plan",
)

BLOCKED_SESSION_ACTIONS: tuple[str, ...] = (
    "real browser control: locked",
    "launching real browsers",
    "opening URLs or navigating pages",
    "screenshots, screen capture, DOM reads, or page extraction",
    "click, type, submit, login, payment, upload, or download",
    "cookie, localStorage, profile, session, password, or token reads",
    "Playwright, browser-use, Stagehand, Maxun, MCP, PyAutoGUI, shell, package, cloud, or desktop execution",
)


@dataclass(frozen=True)
class BrowserSessionPreview:
    session_id: str
    label: str
    mode: str
    status: str
    domain_policy_summary: str
    allowed_now: tuple[str, ...]
    blocked_now: tuple[str, ...]
    created_at: str
    updated_at: str
    notes: tuple[str, ...]


def create_preview_session(label: str = "Browser session preview") -> BrowserSessionPreview:
    now = _now()
    session = BrowserSessionPreview(
        session_id=f"browser-preview-{uuid4().hex[:10]}",
        label=_clean_label(label),
        mode="preview_only",
        status="preview_planned",
        domain_policy_summary="Domain policy preview only; no page or browser state is read.",
        allowed_now=ALLOWED_SESSION_PREVIEW_ACTIONS,
        blocked_now=BLOCKED_SESSION_ACTIONS,
        created_at=now,
        updated_at=now,
        notes=(
            "This is a local preview record, not a real browser session.",
            "Real browser control stays locked until a future permission-gated executor phase.",
            "No browser was launched, navigated, observed, or controlled.",
        ),
    )
    from .session_registry import register_preview_session

    register_preview_session(session)
    return session


def planned_session_preview() -> BrowserSessionPreview:
    return BrowserSessionPreview(
        session_id="browser-preview-plan",
        label="Future BrowserAgent session lifecycle preview",
        mode="preview_only",
        status="locked",
        domain_policy_summary="Future sessions must classify public/private/logged-in/payment/admin pages before any observation.",
        allowed_now=ALLOWED_SESSION_PREVIEW_ACTIONS,
        blocked_now=BLOCKED_SESSION_ACTIONS,
        created_at=_now(),
        updated_at=_now(),
        notes=(
            "Plan step 1: create a preview record.",
            "Plan step 2: apply domain and privacy policy before any future observation.",
            "Plan step 3: require human confirmation for any future external or sensitive action.",
            "Plan step 4: verify results without reading cookies, localStorage, passwords, sessions, or profiles.",
        ),
    )


def _clean_label(label: str) -> str:
    text = " ".join(str(label or "").split())
    return text[:80] if text else "Browser session preview"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
