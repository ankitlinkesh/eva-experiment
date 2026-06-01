from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from ..privacy.redaction import redact_secrets
from .prompt_injection import detect_prompt_injection
from .output_safety import detect_unsafe_output


@dataclass
class GuardrailResult:
    safe: bool
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)
    redactions: list[dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    sanitized: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_llm_guard_available() -> bool:
    try:
        import llm_guard  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def _guard_text(text: str, *, output: bool = False) -> GuardrailResult:
    original = str(text or "")
    lowered = original.lower()
    env_local_name = ".env" + ".local"
    redacted, events = redact_secrets(text)
    warnings: list[str] = []
    if events:
        warnings.append("secret_like_content_redacted")
    injection = detect_prompt_injection(redacted)
    unsafe_output = detect_unsafe_output(redacted) if output else None
    secret_request = any(
        marker in lowered
        for marker in (
            env_local_name,
            "show api key",
            "show me my api key",
            "reveal api key",
            "reveal token",
            "show token",
            "read secret",
            "show password",
        )
    )
    blocked = bool(secret_request or injection.get("blocked") or (unsafe_output or {}).get("blocked"))
    if injection.get("warnings"):
        warnings.extend(injection["warnings"])
    if unsafe_output and unsafe_output.get("warnings"):
        warnings.extend(unsafe_output["warnings"])
    if secret_request:
        warnings.append("secret_access_request")
    return GuardrailResult(
        safe=not blocked and not events,
        blocked=blocked,
        warnings=warnings,
        redactions=events,
        reason=str(
            "Secret, token, password, or .env file access is blocked."
            if secret_request
            else injection.get("reason") or (unsafe_output or {}).get("reason") or ""
        ),
        sanitized=redacted,
    )


def guard_input(text: str, context: dict[str, Any] | None = None) -> GuardrailResult:
    return _guard_text(str(text or ""))


def guard_context(context: dict[str, Any]) -> GuardrailResult:
    return _guard_text(json.dumps(context, ensure_ascii=False, default=str))


def guard_tool_call(tool_call: Any) -> GuardrailResult:
    payload = tool_call.as_dict() if hasattr(tool_call, "as_dict") else tool_call
    text = json.dumps(payload, ensure_ascii=False, default=str)
    result = _guard_text(text)
    suspicious_tools = ("shell", "credential", "password", "token", "cookie")
    if any(item in text.lower() for item in suspicious_tools):
        result.blocked = True
        result.safe = False
        result.warnings.append("suspicious_tool_call_intent")
        result.reason = result.reason or "Tool call appears to request credentials, secrets, or arbitrary shell."
    return result


def guard_output(text: str) -> GuardrailResult:
    return _guard_text(str(text or ""), output=True)
