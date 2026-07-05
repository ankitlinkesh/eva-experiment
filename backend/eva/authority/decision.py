from __future__ import annotations

import hashlib

from .models import ACTION_CATEGORIES, AUTHORITY_MODES, RISK_LEVELS, AuthorityDecision, utc_now


_BLOCKED_CATEGORIES = {
    "external_send",
    "browser_action",
    "desktop_control",
    "terminal",
    "system_change",
    "destructive",
    "local_write",
}


def make_authority_decision(
    *,
    action_type: str = "preview",
    action_category: str = "unknown",
    requested_by: str = "user",
    target_resource: str | None = None,
    capability_id: str | None = None,
    agent_name: str | None = None,
    mode: str | None = None,
    risk_level: str | None = None,
    allowed: bool | None = None,
    requires_approval: bool = False,
    approval_id: str | None = None,
    reason: str = "Authority defaults to a safe preview unless a narrower safe route is selected.",
    blocked_reason: str | None = None,
    rollback_available: bool = False,
    verification_required: bool = False,
    sandbox_only: bool = False,
    real_execution_available: bool = False,
    public_mode_allowed: bool = True,
    private_mode_allowed: bool = True,
) -> AuthorityDecision:
    category = action_category if action_category in ACTION_CATEGORIES else "unknown"
    computed_mode = mode or _default_mode(category)
    if computed_mode not in AUTHORITY_MODES:
        computed_mode = "refused"
    computed_risk = risk_level or _default_risk(category)
    if computed_risk not in RISK_LEVELS:
        computed_risk = "unknown"
    computed_allowed = allowed if allowed is not None else computed_mode in {"preview_only", "read_only", "draft_only", "approval_only", "sandbox_only"}
    if category in _BLOCKED_CATEGORIES and computed_mode not in {"sandbox_only", "real_execution_allowed"}:
        computed_allowed = False
        computed_mode = "real_execution_blocked" if category == "local_write" else "refused"
        blocked_reason = blocked_reason or "Real execution is blocked by Eva's Phase 12G authority spine."
    if category == "unknown" and mode is None:
        computed_allowed = False
    return AuthorityDecision(
        action_id=_action_id(action_type, category, capability_id),
        action_type=action_type,
        action_category=category,
        requested_by=requested_by,
        target_resource=target_resource,
        capability_id=capability_id,
        agent_name=agent_name,
        mode=computed_mode,
        risk_level=computed_risk,
        allowed=bool(computed_allowed),
        requires_approval=requires_approval,
        approval_id=approval_id,
        reason=reason,
        blocked_reason=blocked_reason,
        rollback_available=rollback_available,
        verification_required=verification_required,
        sandbox_only=sandbox_only or computed_mode == "sandbox_only",
        real_execution_available=real_execution_available and computed_mode == "real_execution_allowed",
        public_mode_allowed=public_mode_allowed,
        private_mode_allowed=private_mode_allowed,
        created_at=utc_now(),
    )


def allow_preview_decision(**kwargs: object) -> AuthorityDecision:
    return make_authority_decision(mode="preview_only", allowed=True, real_execution_available=False, **kwargs)


def allow_readonly_decision(**kwargs: object) -> AuthorityDecision:
    return make_authority_decision(mode="read_only", risk_level=str(kwargs.pop("risk_level", "low")), allowed=True, real_execution_available=False, **kwargs)


def allow_draft_decision(**kwargs: object) -> AuthorityDecision:
    return make_authority_decision(mode="draft_only", risk_level=str(kwargs.pop("risk_level", "medium")), allowed=True, real_execution_available=False, **kwargs)


def allow_approval_decision(**kwargs: object) -> AuthorityDecision:
    return make_authority_decision(mode="approval_only", risk_level=str(kwargs.pop("risk_level", "medium")), allowed=True, real_execution_available=False, **kwargs)


def allow_sandbox_decision(**kwargs: object) -> AuthorityDecision:
    return make_authority_decision(
        mode="sandbox_only",
        risk_level=str(kwargs.pop("risk_level", "high")),
        allowed=True,
        sandbox_only=True,
        real_execution_available=False,
        verification_required=bool(kwargs.pop("verification_required", True)),
        rollback_available=bool(kwargs.pop("rollback_available", True)),
        **kwargs,
    )


def allow_real_execution_decision(**kwargs: object) -> AuthorityDecision:
    return make_authority_decision(
        mode="real_execution_allowed",
        risk_level=str(kwargs.pop("risk_level", "medium")),
        allowed=True,
        real_execution_available=True,
        verification_required=bool(kwargs.pop("verification_required", True)),
        rollback_available=bool(kwargs.pop("rollback_available", True)),
        public_mode_allowed=bool(kwargs.pop("public_mode_allowed", False)),
        private_mode_allowed=bool(kwargs.pop("private_mode_allowed", True)),
        **kwargs,
    )


def block_real_execution_decision(**kwargs: object) -> AuthorityDecision:
    return make_authority_decision(
        mode="real_execution_blocked",
        risk_level=str(kwargs.pop("risk_level", "high")),
        allowed=False,
        real_execution_available=False,
        blocked_reason=str(kwargs.pop("blocked_reason", "Real execution is unavailable in this phase.")),
        **kwargs,
    )


def refuse_authority_decision(**kwargs: object) -> AuthorityDecision:
    return make_authority_decision(
        mode="refused",
        risk_level=str(kwargs.pop("risk_level", "high")),
        allowed=False,
        real_execution_available=False,
        blocked_reason=str(kwargs.pop("blocked_reason", "This action is refused by Eva's local authority policy.")),
        public_mode_allowed=False,
        **kwargs,
    )


def _default_mode(category: str) -> str:
    if category == "read":
        return "read_only"
    if category == "draft":
        return "draft_only"
    if category == "approve":
        return "approval_only"
    if category in {"sandbox_apply", "verify", "rollback"}:
        return "sandbox_only"
    if category == "plan":
        return "preview_only"
    if category == "local_write":
        return "real_execution_blocked"
    if category == "real_create_safe_text":
        return "real_execution_blocked"
    if category == "rollback_real_create":
        return "real_execution_blocked"
    if category in _BLOCKED_CATEGORIES:
        return "refused"
    return "refused"


def _default_risk(category: str) -> str:
    if category in {"read", "plan"}:
        return "low"
    if category in {"draft", "approve", "verify"}:
        return "medium"
    if category in {"sandbox_apply", "rollback", "local_write", "real_create_safe_text", "rollback_real_create", "browser_action", "desktop_control", "terminal", "system_change", "external_send"}:
        return "high"
    if category == "destructive":
        return "destructive"
    return "unknown"


def _action_id(action_type: str, category: str, capability_id: str | None) -> str:
    seed = f"{action_type}:{category}:{capability_id or ''}:{utc_now()}"
    return "auth_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]
