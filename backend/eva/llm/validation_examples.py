from __future__ import annotations


VALID_ROUTE_DECISION_PREVIEW = {
    "type": "route_decision_preview",
    "intent": "llm_status",
    "capability": "llm.status",
    "reason": "Read-only status preview; no provider call or tool execution.",
}

VALID_ACTION_PLAN_PREVIEW = {
    "type": "action_plan_preview",
    "summary": "Preview the local validation result.",
    "steps": ["Inspect the preview only.", "Return a safe status response."],
    "safety": "preview_only",
}
