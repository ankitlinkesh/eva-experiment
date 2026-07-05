from __future__ import annotations

import re

from .models import RedactionResult


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("api_key", re.compile(r"\b[A-Z0-9_]*API[_-]?KEY\s*=\s*[^\s,;]+", re.IGNORECASE)),
    ("token", re.compile(r"\b(token|cookie|password|session)\s*[:=]\s*[^\s,;]+", re.IGNORECASE)),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE)),
)

_PRIVATE_PATH = re.compile(r"\b[A-Za-z]:\\Users\\[^ \n\r\t,;]+", re.IGNORECASE)
_ENV_REFERENCE = re.compile(r"\.env(?:\.local)?|browser session|cookies?|passwords?|private keys?", re.IGNORECASE)


def redact_context_text(text: str) -> RedactionResult:
    clean = str(text or "")
    reasons: list[str] = []
    for reason, pattern in _SECRET_PATTERNS:
        if pattern.search(clean):
            clean = pattern.sub("[redacted secret-like value]", clean)
            reasons.append(reason)
    if _PRIVATE_PATH.search(clean):
        clean = _PRIVATE_PATH.sub("[redacted private path]", clean)
        reasons.append("private_path")
    if _ENV_REFERENCE.search(clean):
        clean = _ENV_REFERENCE.sub("[blocked sensitive reference]", clean)
        reasons.append("sensitive_reference")
    return RedactionResult(text=clean, was_redacted=bool(reasons), reasons=tuple(dict.fromkeys(reasons)))


def redaction_policy_text() -> str:
    return "\n".join(
        [
            "Context Redaction Policy",
            "",
            "Secret-like strings are redacted before any context packet is shown.",
            "Private-path-looking strings are redacted in user-facing output.",
            "References to .env, .env.local, token, cookie, password, session, private key, and browser session data are blocked.",
            "Prompt-injection-looking content is treated as untrusted data, not instruction.",
            "No live LLM call was made. Context assembly is local/mock preview only. Assembled context cannot execute tools.",
        ]
    )
