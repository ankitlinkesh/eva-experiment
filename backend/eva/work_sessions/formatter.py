from __future__ import annotations

from .store import get_work_session, list_recent_work_sessions, list_session_events


def format_work_session(session_or_id: object) -> str:
    session_id = _session_id(session_or_id)
    session = get_work_session(session_id)
    if session is None:
        return "\n".join(["Work session", "", f"Session `{session_id}` was not found."])
    specialists = ", ".join(session.selected_specialists) if session.selected_specialists else "none"
    skills = ", ".join(session.selected_skills) if session.selected_skills else "none"
    steps = ", ".join(session.planner_steps[:5]) if session.planner_steps else "none"
    return "\n".join(
        [
            "Work session",
            "",
            f"ID: {session.session_id}",
            f"Status: {session.status}",
            f"Source: {session.source}",
            f"Request: {session.user_request}",
            f"Intent: {session.interpreted_intent or 'unknown'}",
            f"Specialists: {specialists}",
            f"Skills: {skills}",
            f"Workflow: {session.selected_workflow or 'none'}",
            f"Planner steps: {steps}",
            f"Authority: {session.authority_decision or 'not recorded'}",
            f"Approval: {session.approval_id or 'none'}",
            f"Sandbox apply: {session.sandbox_apply_status or 'not observed'}",
            f"Real create: {session.real_create_status or 'not observed'}",
            f"Verification: {session.verification_status or 'not observed'}",
            f"Rollback: {session.rollback_status or 'not observed'}",
            f"Next safe step: {session.next_safe_step or 'Review the latest status before acting.'}",
            f"Final report: {session.final_summary or 'not closed yet'}",
            "",
            "Execution: audit/status only. No browser, desktop, shell, MCP, package, cloud, or broad file action was executed.",
        ]
    )


def format_work_session_timeline(session_or_id: object) -> str:
    session_id = _session_id(session_or_id)
    session = get_work_session(session_id)
    if session is None:
        return "\n".join(["Work session timeline", "", f"Session `{session_id}` was not found."])
    events = list_session_events(session_id)
    lines = [
        "Work session timeline",
        "",
        f"Session: {session.session_id}",
        f"Request: {session.user_request}",
        "",
        "Events:",
    ]
    if not events:
        lines.append("- No events recorded yet.")
    for event in events:
        lines.append(f"- {event.sequence}. {event.event_type}: {event.summary}")
        if event.metadata:
            parts = [f"{key}={value}" for key, value in sorted(event.metadata.items())[:4]]
            if parts:
                lines.append(f"  Metadata: {', '.join(parts)}")
    lines.extend(["", "Execution: timeline only. No task was executed."])
    return "\n".join(lines)


def format_work_sessions_status() -> str:
    recent = list_recent_work_sessions(limit=20)
    active = [item for item in recent if item.status == "active"]
    closed = [item for item in recent if item.status != "active"]
    latest = recent[0] if recent else None
    return "\n".join(
        [
            "Work sessions status",
            "",
            f"Recent sessions: {len(recent)}",
            f"Active sessions: {len(active)}",
            f"Closed/reported sessions: {len(closed)}",
            f"Latest session: {latest.session_id if latest else 'none'}",
            f"Latest request: {latest.user_request if latest else 'No work sessions recorded yet.'}",
            "",
            "Scope: local audit/status only. Session tracking does not enable any new execution path.",
        ]
    )


def summarize_work_session(session_or_id: object) -> str:
    session_id = _session_id(session_or_id)
    session = get_work_session(session_id)
    if session is None:
        return "\n".join(["Work session summary", "", f"Session `{session_id}` was not found."])
    return "\n".join(
        [
            "Work session summary",
            "",
            f"{session.session_id}: {session.interpreted_intent or 'unknown'}; status {session.status}.",
            f"Request: {session.user_request}",
            f"Authority: {session.authority_decision or 'not recorded'}",
            f"Next safe step: {session.next_safe_step or 'Review status before acting.'}",
        ]
    )


def summarize_recent_work_sessions(limit: int = 10) -> str:
    sessions = list_recent_work_sessions(limit=limit)
    lines = ["Work sessions recent", ""]
    if not sessions:
        lines.append("No work sessions recorded yet.")
    for session in sessions:
        lines.append(f"- {session.session_id}: {session.status}; {session.interpreted_intent or 'unknown'}; {session.user_request}")
    lines.extend(["", "Execution: status only."])
    return "\n".join(lines)


def _session_id(session_or_id: object) -> str:
    if hasattr(session_or_id, "session_id"):
        return str(getattr(session_or_id, "session_id"))
    return str(session_or_id or "").strip()
