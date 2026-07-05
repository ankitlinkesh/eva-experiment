from __future__ import annotations

from .models import LLMSessionLimitPolicy, LLMSessionUsagePreview


def get_session_limit_policy() -> LLMSessionLimitPolicy:
    return LLMSessionLimitPolicy(8, 8, 2)


def preview_session_usage(route_previews_used: int = 0, planning_steps_used: int = 0) -> LLMSessionUsagePreview:
    policy = get_session_limit_policy()
    return LLMSessionUsagePreview(route_previews_used, planning_steps_used, route_previews_used <= policy.max_route_previews and planning_steps_used <= policy.max_planning_steps)
