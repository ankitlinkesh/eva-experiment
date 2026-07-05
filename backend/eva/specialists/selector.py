from __future__ import annotations

from .models import SpecialistRole
from .registry import get_specialist, list_specialists


def select_specialists_for_request(request_text: str) -> list[SpecialistRole]:
    text = _normalize(request_text)
    selected: list[str] = []
    if _has_any(text, ("project note", "docs note", "phase note", "fileagent phase", "approved text file", "real create", "sandbox apply", "rollback")):
        selected.append("fileagent_workflow_specialist")
    if _has_any(text, ("inspect project", "inspect this project", "project inventory", "what is this project", "explain this repo", "explain this project", "understand repo", "codebase", "current eva status")):
        selected.append("codebase_onboarding_specialist")
    if _has_any(text, ("draft", "readme", "report", "write", "technical note", "docs note", "project note")):
        selected.append("technical_writer")
    if _has_any(text, ("actually done", "are we done", "proof", "verify this phase", "truth", "reality", "passed", "broken", "failing")):
        selected.append("reality_checker")
    if _has_any(text, ("evidence", "audit", "events", "show proof", "what proof", "status evidence", "what should we do next", "next safe phase")):
        selected.append("evidence_collector")
    if _has_any(text, ("test", "verifier", "verify all", "quick check", "full check", "failed", "broken", "failing")):
        selected.append("test_results_analyzer")
    if _has_any(text, ("safe", "safety", "permission", "authority", "blocked", "real actions", "delete", "send", "browser", "desktop", "terminal", "what should we do next", "next safe phase")):
        selected.append("safety_reviewer")
    if not selected:
        selected.extend(["reality_checker", "safety_reviewer"])
    out: list[SpecialistRole] = []
    for specialist_id in selected:
        item = get_specialist(specialist_id)
        if item and item not in out:
            out.append(item)
    return out


def _normalize(value: str) -> str:
    return " ".join(str(value or "").lower().strip().split())


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)
