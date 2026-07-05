from __future__ import annotations

from .formatter import (
    format_work_session,
    format_work_session_timeline,
    format_work_sessions_status,
    summarize_recent_work_sessions,
)
from .store import find_latest_active_work_session, list_recent_work_sessions


def format_latest_work_session() -> str:
    recent = list_recent_work_sessions(limit=1)
    if not recent:
        return "\n".join(["Work session latest", "", "No work sessions recorded yet."])
    return format_work_session(recent[0].session_id)


def format_audit_timeline() -> str:
    recent = list_recent_work_sessions(limit=1)
    if not recent:
        return "\n".join(["Work session audit timeline", "", "No work sessions recorded yet."])
    return format_work_session_timeline(recent[0].session_id)


def format_work_session_detail(session_id: str) -> str:
    return format_work_session(session_id)


def format_work_session_timeline_by_id(session_id: str) -> str:
    return format_work_session_timeline(session_id)


def summarize_active_or_latest_work_session() -> str:
    active = find_latest_active_work_session()
    if active:
        return format_work_session(active.session_id)
    return format_latest_work_session()
