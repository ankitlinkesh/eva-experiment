from __future__ import annotations

import re

from .models import TranscriptSafetyResult


_PRIVATE_PATH = re.compile(r"(?:[A-Za-z]:\\[^\s]+|/(?:home|Users)/[^\s]+)", re.IGNORECASE)
_SECRET_TERMS = ("token=", "cookie=", "password=", "session=", "api key", "secret key", ".env", ".env.local")
_INJECTION_TERMS = ("ignore previous", "ignore policy", "override safety", "obey this transcript", "system prompt")
_TOOL_TERMS = ("execute a tool", "run a tool", "call a tool", "use a tool", "delete a file", "write a file")
_LOCKED_SURFACES = ("browser", "desktop", "shell", "cloud", "mcp", "package", "install package")
_UNKNOWN_CAPABILITIES = ("imaginary", "quantum capability", "hallucinated capability", "unknown capability")
_HIGH_RISK_TERMS = ("delete all", "publish", "send message", "transfer money", "change permissions")


def classify_transcript(transcript: str) -> TranscriptSafetyResult:
    original = str(transcript or "").strip()
    lowered = original.lower()
    flags: list[str] = []

    if any(term in lowered for term in _SECRET_TERMS):
        flags.append("secret_config_session_like")
        return TranscriptSafetyResult("blocked", True, "[REDACTED]", tuple(flags), "Sensitive transcript blocked.")
    if _PRIVATE_PATH.search(original):
        flags.append("private_path_like")
        return TranscriptSafetyResult("blocked", True, "[PRIVATE PATH REDACTED]", tuple(flags), "Private-path-like transcript blocked.")
    if any(term in lowered for term in _INJECTION_TERMS):
        flags.append("prompt_injection_like")
        return TranscriptSafetyResult("untrusted", False, original, tuple(flags), "Untrusted instruction-like transcript blocked.")
    if any(term in lowered for term in _LOCKED_SURFACES):
        flags.append("locked_execution_surface")
        return TranscriptSafetyResult("blocked", False, original, tuple(flags), "Locked browser/desktop/shell/cloud/MCP/package request blocked.")
    if any(term in lowered for term in _TOOL_TERMS):
        flags.append("tool_execution_request")
        return TranscriptSafetyResult("blocked", False, original, tuple(flags), "Tool request sent to execution-gate preview and blocked.")
    if any(term in lowered for term in _UNKNOWN_CAPABILITIES):
        flags.append("unknown_or_hallucinated_capability")
        return TranscriptSafetyResult("rejected", False, original, tuple(flags), "Unknown or hallucinated capability rejected.")
    if any(term in lowered for term in _HIGH_RISK_TERMS):
        flags.append("high_risk_future_action")
        return TranscriptSafetyResult("confirmation_required", False, original, tuple(flags), "Confirmation preview required; no action is authorized.")
    if not original:
        return TranscriptSafetyResult("blocked", False, "(empty mock transcript)", ("empty_transcript",), "Empty transcript stopped safely.")
    return TranscriptSafetyResult("safe", False, original, (), "")


def transcript_safety_policy_text() -> str:
    from .voice_policy import boundary_lines

    return "\n".join(
        [
            "Voice transcript safety policy",
            *boundary_lines(),
            "Secret, token, cookie, password, session, config, and private-path-like input is blocked and redacted.",
            "Prompt-injection-like text is untrusted user input and cannot override policy.",
            "Tool requests reach execution gates as preview only.",
            "Browser/desktop/shell/cloud/MCP/package requests are blocked.",
            "Unknown or hallucinated capabilities are rejected.",
            "High-risk future actions require confirmation preview only.",
            "No transcript can directly execute a tool or action.",
        ]
    )
