"""Local WorkSession and audit timeline helpers for Eva."""

from .store import (
    add_session_event,
    close_work_session,
    create_work_session,
    find_latest_active_work_session,
    get_work_session,
    list_recent_work_sessions,
)

__all__ = [
    "add_session_event",
    "close_work_session",
    "create_work_session",
    "find_latest_active_work_session",
    "get_work_session",
    "list_recent_work_sessions",
]
