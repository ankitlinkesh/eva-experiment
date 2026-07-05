from __future__ import annotations


def classify_workflow_risk(request: str, category: str) -> str:
    text = str(request or "").lower()
    if category == "refusal_or_blocked":
        return "forbidden"
    if any(term in text for term in ("secret", "token", "cookie", "password", ".env", "execute", "shell", "browser", "desktop", "cloud", "mcp")):
        return "critical"
    if "high risk" in text or "future" in text or "fileagent" in text:
        return "high"
    if category in {"fileagent_project_note_preview", "verification_summary", "agent_loop_preview"}:
        return "medium"
    return "low"


def permission_for_risk(risk_level: str) -> str:
    if risk_level in {"critical", "forbidden"}:
        return "blocked_preview"
    if risk_level == "high":
        return "future_approval_required"
    return "preview_only"
