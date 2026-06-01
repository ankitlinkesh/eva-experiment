from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from ..privacy.redaction import redact_secrets


PENDING_ACTION_STATUSES = {
    "pending_confirmation",
    "pending_override",
    "confirmed",
    "confirmed_but_executor_unavailable",
    "cancelled",
    "expired",
    "refused",
}
RISK_LEVELS = {"low", "medium", "high", "critical"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def expires_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _clean(value: Any, limit: int = 1000) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    redacted, _events = redact_secrets(text)
    return redacted[:limit]


def sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        clean_key = _clean(key, 80)
        if not clean_key:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[clean_key] = _clean(value, 500) if isinstance(value, str) else value
        elif isinstance(value, list):
            safe[clean_key] = [_clean(item, 200) for item in value[:10]]
        elif isinstance(value, dict):
            safe[clean_key] = {str(k)[:80]: _clean(v, 200) for k, v in list(value.items())[:10]}
        else:
            safe[clean_key] = _clean(value, 200)
    return safe


@dataclass
class EvaPendingAction:
    id: str
    request_id: str | None
    task_id: str | None
    created_at: str
    expires_at: str
    status: str
    action_type: str
    risk_level: str
    risk_category: str
    summary: str
    target: str | None = None
    payload_summary: str | None = None
    requires_confirmation: bool = False
    requires_override: bool = False
    confirmation_phrase: str | None = None
    source: str = "normal_chat"
    selected_agent: str | None = None
    proposed_action_ref: str | None = None
    executor_available: bool = False
    executor_name: str | None = None
    safety_reason: str = ""
    provenance: str = "pending_action_ledger"
    redacted_payload: dict[str, Any] | None = field(default_factory=dict)

    @classmethod
    def new(
        cls,
        *,
        action_type: str,
        risk_level: str,
        risk_category: str,
        summary: str,
        request_id: str | None = None,
        task_id: str | None = None,
        target: str | None = None,
        payload_summary: str | None = None,
        requires_confirmation: bool = False,
        requires_override: bool = False,
        confirmation_phrase: str | None = None,
        source: str = "normal_chat",
        selected_agent: str | None = None,
        proposed_action_ref: str | None = None,
        executor_available: bool = False,
        executor_name: str | None = None,
        safety_reason: str = "",
        provenance: str = "pending_action_ledger",
        redacted_payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
        status: str | None = None,
    ) -> "EvaPendingAction":
        if ttl_seconds is None:
            ttl_seconds = 300 if requires_override or risk_category in {"destructive_file_action", "system_change"} else 120
        initial_status = status or ("pending_override" if requires_override else "pending_confirmation")
        return cls(
            id=f"act_{uuid4().hex[:12]}",
            request_id=request_id,
            task_id=task_id,
            created_at=now_iso(),
            expires_at=expires_iso(ttl_seconds),
            status=_valid_status(initial_status),
            action_type=_clean(action_type, 160),
            risk_level=_valid_risk_level(risk_level),
            risk_category=_clean(risk_category, 160),
            summary=_clean(summary, 1000),
            target=_clean(target, 300) or None,
            payload_summary=_clean(payload_summary, 500) or None,
            requires_confirmation=bool(requires_confirmation or (not requires_override and initial_status == "pending_confirmation")),
            requires_override=bool(requires_override),
            confirmation_phrase=confirmation_phrase or ("confirm override" if requires_override else None),
            source=_clean(source, 160) or "normal_chat",
            selected_agent=_clean(selected_agent, 120) or None,
            proposed_action_ref=_clean(proposed_action_ref, 160) or None,
            executor_available=bool(executor_available),
            executor_name=_clean(executor_name, 160) or None,
            safety_reason=_clean(safety_reason, 1000),
            provenance=_clean(provenance, 160) or "pending_action_ledger",
            redacted_payload=sanitize_payload(redacted_payload),
        )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    model_dump = as_dict

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvaPendingAction":
        data = dict(value)
        data["status"] = _valid_status(str(data.get("status") or "pending_confirmation"))
        data["risk_level"] = _valid_risk_level(str(data.get("risk_level") or "medium"))
        data["redacted_payload"] = sanitize_payload(data.get("redacted_payload"))
        return cls(**data)

    def is_expired(self, now: datetime | None = None) -> bool:
        if self.status in {"cancelled", "confirmed", "confirmed_but_executor_unavailable", "expired", "refused"}:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at)
        except ValueError:
            return True
        return expires <= (now or datetime.now(timezone.utc))


@dataclass
class EvaPendingActionResult:
    success: bool
    action_id: str | None
    status: str
    message: str
    action: EvaPendingAction | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "action_id": self.action_id,
            "status": self.status,
            "message": self.message,
            "action": self.action.as_dict() if self.action else None,
        }

    model_dump = as_dict


def _valid_status(value: str) -> str:
    return value if value in PENDING_ACTION_STATUSES else "pending_confirmation"


def _valid_risk_level(value: str) -> str:
    return value if value in RISK_LEVELS else "medium"
