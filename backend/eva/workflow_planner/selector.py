from __future__ import annotations

from .models import WorkflowTemplate
from .workflow_catalog import list_workflow_templates


def select_workflow_template(request: str) -> tuple[WorkflowTemplate, float]:
    text = " ".join(str(request or "").lower().split())
    templates = list_workflow_templates()
    if _is_unsafe(text):
        return _by_category("refusal_or_blocked", templates), 0.99
    if "missing approval precondition" in text:
        return _by_category("fileagent_project_note_preview", templates), 0.84
    if "high risk" in text or "project note" in text or "fileagent" in text:
        return _by_category("fileagent_project_note_preview", templates), 0.88
    best = _by_category("planning_only", templates)
    best_score = 0.55
    for template in templates:
        score = sum(1 for keyword in template.relevance_keywords if keyword in text)
        if score > best_score:
            best = template
            best_score = float(score)
    return best, min(0.99, 0.55 + best_score * 0.12)


def _by_category(category: str, templates: tuple[WorkflowTemplate, ...]) -> WorkflowTemplate:
    for template in templates:
        if template.category == category:
            return template
    return templates[0]


def _is_unsafe(text: str) -> bool:
    blocked_terms = (
        "execute tool",
        "run shell",
        "powershell",
        "terminal",
        "browser",
        "desktop",
        "cloud",
        "mcp",
        "package",
        ".env",
        "token",
        "cookie",
        "password",
        "session",
        "secret",
        "arbitrary file",
        "write arbitrary",
        "super_execute",
    )
    return any(term in text for term in blocked_terms)
