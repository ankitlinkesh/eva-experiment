from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


ACTION_CATEGORIES = {
    "read",
    "plan",
    "draft",
    "approve",
    "sandbox_apply",
    "verify",
    "rollback",
    "local_write",
    "real_create_safe_text",
    "rollback_real_create",
    "external_send",
    "browser_action",
    "desktop_control",
    "terminal",
    "system_change",
    "destructive",
    "unknown",
}

AUTHORITY_MODES = {
    "preview_only",
    "read_only",
    "draft_only",
    "approval_only",
    "sandbox_only",
    "real_execution_blocked",
    "real_execution_allowed",
    "refused",
}

RISK_LEVELS = {"low", "medium", "high", "destructive", "unknown"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class AuthorityDecision:
    action_id: str
    action_type: str
    action_category: str
    requested_by: str
    target_resource: str | None
    capability_id: str | None
    agent_name: str | None
    mode: str
    risk_level: str
    allowed: bool
    requires_approval: bool
    approval_id: str | None
    reason: str
    blocked_reason: str | None
    rollback_available: bool
    verification_required: bool
    sandbox_only: bool
    real_execution_available: bool
    public_mode_allowed: bool
    private_mode_allowed: bool
    created_at: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def __str__(self) -> str:
        from .formatter import format_authority_decision

        return format_authority_decision(self)
