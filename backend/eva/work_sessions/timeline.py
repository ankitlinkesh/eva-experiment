from __future__ import annotations

import re

from .store import add_session_event, close_work_session, create_work_session, update_work_session


def record_eva_ask_work_session(
    *,
    request_text: str,
    route: object,
    decision: object,
    specialists: list[object],
    skills: list[object],
    workflow: object | None,
    next_safe_step: str,
) -> str:
    session = create_work_session(request_text, source="eva ask")
    specialist_ids = [str(getattr(item, "id", item)) for item in specialists[:6]]
    skill_ids = [str(getattr(item, "id", item)) for item in skills[:6]]
    workflow_id = str(getattr(workflow, "id", "")) if workflow else ""
    intent = str(getattr(route, "intent", "unknown"))
    if not workflow_id and intent.startswith("real_create"):
        workflow_id = "fileagent_project_note_create"
    approval_id = _approval_id(request_text)
    planner_steps = _planner_steps(request_text)
    authority = _decision_summary(decision)
    update_work_session(
        session.session_id,
        interpreted_intent=intent,
        selected_specialists=specialist_ids,
        selected_skills=skill_ids,
        selected_workflow=workflow_id,
        planner_steps=planner_steps,
        authority_decision=authority,
        approval_id=approval_id,
        sandbox_apply_status=_workflow_value("latest_sandbox_apply"),
        real_create_status=_workflow_value("latest_real_create"),
        verification_status="visible through verifier/status surfaces",
        rollback_status=_workflow_value("latest_rollback_available"),
        next_safe_step=next_safe_step,
    )
    add_session_event(session.session_id, "intent_routed", f"Intent `{getattr(route, 'intent', 'unknown')}` routed to `{getattr(route, 'routed_to', 'authority_preview')}`.")
    if specialist_ids:
        add_session_event(session.session_id, "specialist_selected", "Selected specialist route.", {"specialists": ", ".join(specialist_ids)})
    if skill_ids:
        add_session_event(session.session_id, "skill_selected", "Selected skill route.", {"skills": ", ".join(skill_ids)})
    if workflow_id:
        add_session_event(session.session_id, "workflow_selected", "Selected workflow route.", {"workflow": workflow_id})
    if approval_id:
        add_session_event(session.session_id, "approval_selected", "Selected FileAgent approval record.", {"approval_id": approval_id})
    if planner_steps:
        add_session_event(session.session_id, "planner_steps_created", "Planner preview steps recorded.", {"steps": ", ".join(planner_steps[:5])})
    add_session_event(session.session_id, "authority_decision", authority, {"mode": str(getattr(decision, "mode", "preview"))})
    add_session_event(session.session_id, "sandbox_apply_seen", _workflow_value("latest_sandbox_apply"))
    add_session_event(session.session_id, "real_create_seen", _workflow_value("latest_real_create"))
    add_session_event(session.session_id, "verification_seen", "Fresh verifier execution was not run by WorkSession tracking.")
    add_session_event(session.session_id, "rollback_available", _workflow_value("latest_rollback_available"))
    return session.session_id


def finalize_work_session(session_id: str | None, body: str, status: str = "reported") -> None:
    if not session_id:
        return
    summary = " ".join(str(body or "").split())[:500] or "Response returned."
    try:
        approval_id = _approval_id(body)
        if approval_id:
            add_session_event(session_id, "approval_selected", "Response referenced FileAgent approval evidence.", {"approval_id": approval_id})
        lowered = str(body or "").lower()
        if "real create completed" in lowered or "real-create verification" in lowered:
            add_session_event(session_id, "real_create_seen", "Real-create evidence appeared in final response.")
            add_session_event(session_id, "verification_seen", "Real-create verification evidence appeared in final response.")
        if "rollback" in lowered:
            add_session_event(session_id, "rollback_available", "Rollback status or phrase appeared in final response.")
        close_work_session(session_id, status, summary)
    except Exception:
        return


def _decision_summary(decision: object) -> str:
    mode = str(getattr(decision, "mode", "preview"))
    allowed = "allowed" if bool(getattr(decision, "allowed", False)) else "blocked"
    category = str(getattr(decision, "action_category", "unknown"))
    return f"{mode}; {allowed}; {category}"


def _planner_steps(request_text: str) -> list[str]:
    try:
        from ..planner.decomposer import create_task_plan

        plan = create_task_plan(request_text)
        return [step.title for step in plan.steps[:6]]
    except Exception:
        return []


def _workflow_value(name: str) -> str:
    try:
        from ..skills.workflow_state import summarize_fileagent_workflow_state

        state = summarize_fileagent_workflow_state()
        item = getattr(state, name)
        return str(getattr(item, "status", item))
    except Exception:
        return "not observed"


def _approval_id(text: object) -> str:
    match = re.search(r"\b(fap_[A-Za-z0-9]+)\b", str(text or ""))
    return match.group(1) if match else ""
