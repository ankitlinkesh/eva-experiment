from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .redaction import redact_secrets


@dataclass(frozen=True)
class CloudContextRequest:
    user_request: str
    candidate_context: dict[str, Any]
    context_sources: list[str]
    purpose: str
    contains_private_content: bool
    contains_raw_file: bool
    contains_raw_chat: bool
    contains_raw_screenshot: bool
    user_confirmed_private_cloud_share: bool = False


@dataclass(frozen=True)
class CloudContextResult:
    allowed: bool
    sanitized_prompt: str
    blocked_reason: str | None = None
    needs_confirmation: bool = False
    confirmation_message: str | None = None
    redaction_events: list[dict] = field(default_factory=list)
    minimization_summary: str = ""
    ui_events: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CloudContextFirewall:
    def prepare(self, request: CloudContextRequest) -> CloudContextResult:
        ui_events = [{"type": "cloud_context_minimized", "purpose": request.purpose}]
        raw_flags = {
            "raw_file": request.contains_raw_file,
            "raw_chat": request.contains_raw_chat,
            "raw_screenshot": request.contains_raw_screenshot,
        }
        if (request.contains_private_content or any(raw_flags.values())) and not request.user_confirmed_private_cloud_share:
            ui_events.append({"type": "cloud_context_requires_confirmation", "sources": request.context_sources})
            return CloudContextResult(
                allowed=False,
                sanitized_prompt=f"User request: {request.user_request}",
                blocked_reason="private_context_requires_confirmation",
                needs_confirmation=True,
                confirmation_message="This may send private local context to a cloud model. Confirm before sharing it.",
                minimization_summary="Current request only; raw private context withheld locally.",
                ui_events=ui_events,
            )

        minimized = self._minimize_context(request.candidate_context)
        prompt = "User request:\n" + request.user_request.strip() + "\n\nMinimized local context:\n" + json.dumps(minimized, ensure_ascii=False, indent=2)
        redacted, events = redact_secrets(prompt)
        if events:
            ui_events.append({"type": "cloud_context_redacted", "count": len(events)})
        return CloudContextResult(
            allowed=True,
            sanitized_prompt=redacted,
            redaction_events=events,
            minimization_summary=f"Included {len(minimized)} minimized context field(s) from {', '.join(request.context_sources) or 'none'}.",
            ui_events=ui_events,
        )

    def _minimize_context(self, context: dict[str, Any]) -> dict[str, Any]:
        minimized: dict[str, Any] = {}
        for key, value in (context or {}).items():
            if isinstance(value, list):
                minimized[key] = value[:5]
            elif isinstance(value, dict):
                minimized[key] = {str(k): str(v)[:500] for k, v in list(value.items())[:8]}
            else:
                minimized[key] = str(value)[:1000]
        return minimized
