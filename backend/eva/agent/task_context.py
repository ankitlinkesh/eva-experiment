from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


TASK_CONTEXT_TTL_MINUTES = 10
_SESSION_KEY = "task_context"
_CURRENT_CONTEXT: "TaskContext | None" = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).isoformat()


def _expires() -> str:
    return (_now() + timedelta(minutes=TASK_CONTEXT_TTL_MINUTES)).isoformat()


def _clean(value: Any, limit: int = 500) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())[:limit]


@dataclass(frozen=True)
class TaskContext:
    task_id: str
    user_request: str
    active_intent: str | None = None
    target_app: str | None = None
    target_platform: str | None = None
    target_query: str | None = None
    target_url: str | None = None
    target_domain: str | None = None
    target_title: str | None = None
    target_contact: str | None = None
    target_message: str | None = None
    expected_result: str | None = None
    last_action: str | None = None
    last_tool: str | None = None
    last_observation: dict[str, Any] | None = None
    last_verification: dict[str, Any] | None = None
    unresolved_followup: str | None = None
    needs_activation: bool = False
    created_at: str = ""
    updated_at: str = ""
    expires_at: str = ""
    provenance: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def fresh(cls, user_request: str = "", **updates: Any) -> "TaskContext":
        now = _iso()
        fields = {
            "task_id": uuid4().hex,
            "user_request": _clean(user_request),
            "created_at": now,
            "updated_at": now,
            "expires_at": _expires(),
        }
        fields.update(_sanitize_updates(updates))
        return cls(**fields)


def _sanitize_updates(updates: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    string_fields = {
        "user_request",
        "active_intent",
        "target_app",
        "target_platform",
        "target_query",
        "target_url",
        "target_domain",
        "target_title",
        "target_contact",
        "target_message",
        "expected_result",
        "last_action",
        "last_tool",
        "unresolved_followup",
        "provenance",
    }
    for key, value in updates.items():
        if key in string_fields:
            sanitized[key] = _clean(value, 1000 if key == "target_message" else 500) or None
        elif key in {"last_observation", "last_verification"}:
            sanitized[key] = value if isinstance(value, dict) else None
        elif key == "needs_activation":
            sanitized[key] = bool(value)
        elif key in {"task_id", "created_at", "updated_at", "expires_at"} and value:
            sanitized[key] = str(value)
    return sanitized


def _is_expired(context: TaskContext | None) -> bool:
    if context is None:
        return True
    try:
        return datetime.fromisoformat(context.expires_at) <= _now()
    except ValueError:
        return True


def _coerce(value: Any) -> TaskContext | None:
    if isinstance(value, TaskContext):
        return value
    if isinstance(value, dict):
        try:
            return TaskContext(**value)
        except TypeError:
            return None
    return None


def get_current_task_context(session_context: dict[str, Any] | None = None) -> TaskContext | None:
    global _CURRENT_CONTEXT
    context = _coerce(session_context.get(_SESSION_KEY)) if isinstance(session_context, dict) else _CURRENT_CONTEXT
    if _is_expired(context):
        clear_task_context("expired", session_context)
        return None
    return context


def update_task_context(session_context: dict[str, Any] | None = None, **updates: Any) -> TaskContext:
    global _CURRENT_CONTEXT
    existing = get_current_task_context(session_context)
    if existing is None:
        context = TaskContext.fresh(**updates)
    else:
        fields = _sanitize_updates(updates)
        fields["updated_at"] = _iso()
        fields["expires_at"] = _expires()
        context = replace(existing, **fields)
    if isinstance(session_context, dict):
        session_context[_SESSION_KEY] = context.as_dict()
    _CURRENT_CONTEXT = context
    return context


def clear_task_context(reason: str = "", session_context: dict[str, Any] | None = None) -> None:
    global _CURRENT_CONTEXT
    if isinstance(session_context, dict):
        session_context.pop(_SESSION_KEY, None)
        session_context["task_context_cleared_reason"] = _clean(reason)
    _CURRENT_CONTEXT = None


def mark_needs_activation(target: str | dict[str, Any] | None = None, session_context: dict[str, Any] | None = None) -> TaskContext:
    updates: dict[str, Any] = {"needs_activation": True}
    if isinstance(target, dict):
        updates.update(target)
    elif target:
        updates["target_query"] = str(target)
    return update_task_context(session_context, **updates)


def _domain_for_platform(platform: str | None) -> str | None:
    clean = (platform or "").lower()
    if clean == "youtube":
        return "youtube.com"
    if clean == "github":
        return "github.com"
    if clean in {"hugging face", "huggingface"}:
        return "huggingface.co"
    if clean in {"stack overflow", "stackoverflow"}:
        return "stackoverflow.com"
    if clean == "chatgpt":
        return "chatgpt.com"
    if clean == "whatsapp":
        return "whatsapp"
    return None


def resolve_followup_reference(message: str, context: TaskContext | None) -> dict[str, Any] | None:
    if context is None:
        return None
    text = _clean(message).lower()
    if not text:
        return None
    if text in {"play it", "play it now", "open it", "open it now"} and context.target_platform in {"youtube", "spotify"}:
        return {
            "intent": "play",
            "target_platform": context.target_platform,
            "target_query": context.target_query,
            "needs_activation": True,
        }
    if text in {"verify it", "verify this", "verify results", "verify the results", "can you verify the results", "can u verify the results"}:
        return {
            "intent": "verify",
            "target_platform": context.target_platform,
            "target_domain": context.target_domain or _domain_for_platform(context.target_platform),
            "target_query": context.target_query,
            "target_url": context.target_url,
        }
    if text in {"summarize it", "summarize this", "save it", "copy it"}:
        return {
            "intent": text.split()[0],
            "target_platform": context.target_platform,
            "target_domain": context.target_domain or _domain_for_platform(context.target_platform),
            "target_url": context.target_url,
            "target_query": context.target_query,
        }
    return None


def get_last_browser_target(session_context: dict[str, Any] | None = None) -> TaskContext | None:
    context = get_current_task_context(session_context)
    if context and (context.target_domain or context.target_platform in {"youtube", "github", "hugging face", "stackoverflow", "chatgpt"}):
        return context
    return None


def get_last_media_target(session_context: dict[str, Any] | None = None) -> TaskContext | None:
    context = get_current_task_context(session_context)
    if context and context.target_platform in {"spotify", "youtube"}:
        return context
    return None


def get_last_message_target(session_context: dict[str, Any] | None = None) -> TaskContext | None:
    context = get_current_task_context(session_context)
    if context and (context.target_contact or context.target_message):
        return context
    return None
