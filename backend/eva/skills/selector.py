from __future__ import annotations

from .models import EvaSkill, EvaWorkflow
from .registry import get_workflow, list_skills


def select_skills_for_request(request_text: str) -> list[EvaSkill]:
    text = _normalize(request_text)
    selected: list[EvaSkill] = []
    for skill in list_skills():
        if _matches_skill(text, skill.id):
            selected.append(skill)
    if not selected:
        selected = [skill for skill in list_skills() if skill.id == "safety_status_review"]
    return selected


def select_workflow_for_request(request_text: str) -> EvaWorkflow | None:
    text = _normalize(request_text)
    if _has_any(text, ("project note", "docs note", "phase note", "latest fileagent phase", "safe markdown note", "approved docs file")):
        return get_workflow("fileagent_project_note_create")
    return None


def _matches_skill(text: str, skill_id: str) -> bool:
    if skill_id == "fileagent_create_project_note":
        return _has_any(text, ("project note", "docs note", "phase note", "latest fileagent phase", "safe markdown note"))
    if skill_id == "fileagent_safe_draft":
        return _has_any(text, ("draft", "readme", "report", "do not apply", "preview"))
    if skill_id == "project_inspection_readonly":
        return _has_any(text, ("inspect project", "inspect this project", "project inventory", "what is this project", "explain this repo", "explain this project", "understand repo", "current eva status"))
    if skill_id == "verification_before_completion":
        return _has_any(text, ("actually done", "are we done", "proof", "verify this phase", "verifier", "tests passed", "what is broken", "what failed"))
    if skill_id == "safety_status_review":
        return _has_any(text, ("safe", "safety", "permission", "authority", "blocked", "real actions", "delete", "send", "browser", "terminal", "what should we do next"))
    return False


def _normalize(value: str) -> str:
    return " ".join(str(value or "").lower().strip().split())


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)
