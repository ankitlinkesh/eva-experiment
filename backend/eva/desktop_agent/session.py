from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .models import DesktopSessionPreview


ALLOWED_DESKTOP_SESSION_PREVIEW_ACTIONS: tuple[str, ...] = (
    "create preview-only desktop session records",
    "list preview desktop sessions",
    "show latest desktop session preview",
    "show app/window status schema previews",
    "show active context schema preview",
    "show desktop observation readiness gaps",
    "explain locked observation/control boundaries",
)

BLOCKED_DESKTOP_SESSION_ACTIONS: tuple[str, ...] = (
    "real screen capture and screenshots",
    "real window enumeration",
    "real app inspection",
    "active app or active window detection",
    "app launching",
    "mouse movement, clicking, or dragging",
    "keyboard typing or hotkeys",
    "clipboard read/write",
    "file dialog automation",
    "terminal, shell, or package execution",
    "browser/desktop automation",
    "PyAutoGUI, Playwright, MCP, cloud, or package calls",
    "secret, password, token, cookie, browser-session, and private-data reads",
)


def create_preview_session(label: str = "Desktop session preview") -> DesktopSessionPreview:
    now = _now()
    session = DesktopSessionPreview(
        session_id=f"desktop-preview-{uuid4().hex[:10]}",
        label=_clean_label(label),
        mode="preview_only",
        status="preview_planned",
        app_window_policy_summary="App/window status schemas are previews only; no real apps, windows, or screen state are inspected.",
        allowed_now=ALLOWED_DESKTOP_SESSION_PREVIEW_ACTIONS,
        blocked_now=BLOCKED_DESKTOP_SESSION_ACTIONS,
        created_at=now,
        updated_at=now,
        notes=(
            "This is a local preview record, not a real desktop session.",
            "Real desktop observation and control stay locked until a future permission-gated phase.",
            "No screen was captured, no windows were enumerated, and no app was inspected or controlled.",
        ),
    )
    from .session_registry import register_preview_session

    register_preview_session(session)
    return session


def planned_session_preview() -> DesktopSessionPreview:
    now = _now()
    return DesktopSessionPreview(
        session_id="desktop-preview-plan",
        label="Future DesktopAgent session lifecycle preview",
        mode="preview_only",
        status="locked",
        app_window_policy_summary="Future sessions must classify app risk, privacy sensitivity, UI target confidence, and user permission before any observation.",
        allowed_now=ALLOWED_DESKTOP_SESSION_PREVIEW_ACTIONS,
        blocked_now=BLOCKED_DESKTOP_SESSION_ACTIONS,
        created_at=now,
        updated_at=now,
        notes=(
            "Plan step 1: create a preview-only desktop session record.",
            "Plan step 2: apply app/window/privacy policy before future observation.",
            "Plan step 3: require explicit user command and permission for any future screen read.",
            "Plan step 4: require high-confidence UI targets before any future click/type action.",
            "Plan step 5: verify results locally and record audit evidence before continuing.",
        ),
    )


def _clean_label(label: str) -> str:
    text = " ".join(str(label or "").split())
    return text[:80] if text else "Desktop session preview"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
