from __future__ import annotations

from collections import deque

from .models import DesktopSessionPreview


_SESSIONS: deque[DesktopSessionPreview] = deque(maxlen=20)


def register_preview_session(session: DesktopSessionPreview) -> DesktopSessionPreview:
    _SESSIONS.appendleft(session)
    return session


def list_preview_sessions(limit: int = 10) -> list[DesktopSessionPreview]:
    safe_limit = max(1, min(int(limit or 10), 20))
    return list(_SESSIONS)[:safe_limit]


def get_latest_preview_session() -> DesktopSessionPreview | None:
    return _SESSIONS[0] if _SESSIONS else None


def clear_preview_sessions_for_tests() -> None:
    _SESSIONS.clear()
