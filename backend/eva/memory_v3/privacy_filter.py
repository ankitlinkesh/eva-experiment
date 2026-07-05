from __future__ import annotations

import re


_WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\(?:[^\\\s]+\\)*[^\\\s]*")
_TOKEN_RE = re.compile(r"(?i)\b(token|password|cookie|api[_-]?key|bearer|session)\b\s*[:=]?\s*\S*")


def classify_privacy(text: str) -> tuple[str, tuple[str, ...], str]:
    lowered = str(text or "").lower()
    flags: list[str] = []
    if "raw memory database" in lowered or "raw memory db" in lowered or "dump memory" in lowered:
        return "blocked", ("raw_memory_db_dump",), "Raw memory database dumps are blocked."
    if _WINDOWS_PATH_RE.search(str(text or "")):
        return "sensitive_private_path", ("private_path_like",), "Private-path-like memory is blocked or redacted."
    if any(term in lowered for term in ("token", "password", "cookie", "bearer", "api key", "api_key")):
        return "sensitive_credential_or_token", ("credential_or_token_like",), "Credential-like memory is blocked."
    if "session" in lowered:
        return "sensitive_session_or_cookie", ("session_or_cookie_like",), "Session-like memory is blocked."
    if "secret" in lowered or ".env" in lowered:
        return "sensitive_possible_secret", ("secret_like",), "Secret-like memory is blocked."
    if "private" in lowered or "personal" in lowered:
        return "private_user_context", ("private_user_context",), ""
    if "prefer" in lowered or "remember" in lowered:
        return "normal_preference", tuple(flags), ""
    return "public_project_note", tuple(flags), ""


def redact_memory_text(text: str) -> str:
    redacted = _WINDOWS_PATH_RE.sub("[PRIVATE_PATH]", str(text or ""))
    redacted = _TOKEN_RE.sub("[REDACTED_SECRET]", redacted)
    return " ".join(redacted.split())


def privacy_policy_text() -> str:
    from .memory_policy import boundary_lines

    return "\n".join(
        [
            "Memory v3 privacy filter",
            *boundary_lines(),
            "Privacy behavior:",
            "- Secrets, credentials, tokens, cookies, sessions, and private paths are blocked or redacted.",
            "- Raw memory database dumps are blocked.",
            "- User-facing output uses safe summaries, never raw sensitive values.",
        ]
    )
