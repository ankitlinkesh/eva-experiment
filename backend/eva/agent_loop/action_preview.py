from __future__ import annotations

from .loop_policy import ALLOWED_PREVIEW_ACTION_TYPES
from .models import ActionPreview


def make_action_preview(
    index: int,
    action_type: str,
    capability_requested: str,
    *,
    risk_level: str = "low",
    blocked_reason: str = "",
    permission_class: str = "preview_only",
) -> ActionPreview:
    safe_type = action_type if action_type in ALLOWED_PREVIEW_ACTION_TYPES else "refusal_preview"
    return ActionPreview(
        action_id=f"alp_{index:02d}",
        action_type=safe_type,
        capability_requested=capability_requested,
        permission_class=permission_class,
        risk_level=risk_level,
        execution_status="preview_only",
        required_approval="future explicit approval required if execution ever exists",
        blocked_reason=blocked_reason,
        verification_requirement="Verify preview safety; do not execute tools.",
    )


def blocked_action_preview(index: int, capability_requested: str, reason: str) -> ActionPreview:
    return make_action_preview(
        index,
        "refusal_preview",
        capability_requested,
        risk_level="high",
        blocked_reason=reason,
        permission_class="blocked_preview",
    )
