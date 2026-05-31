from __future__ import annotations

import re
from typing import Callable


Pattern = tuple[str, str, str | Callable[[re.Match[str]], str]]


def _event(kind: str, match: re.Match[str]) -> dict:
    return {"type": kind, "start": match.start(), "end": match.end()}


def redact_secrets(text: str) -> tuple[str, list[dict]]:
    source = str(text or "")
    events: list[dict] = []

    patterns: list[Pattern] = [
        ("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
        ("github_token", r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b", "[REDACTED_TOKEN]"),
        ("api_key", r"\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}|gsk_[A-Za-z0-9_-]{20,})\b", "[REDACTED_API_KEY]"),
        ("bearer_token", r"\bbearer\s+[A-Za-z0-9._~+/=-]{8,}\b", "[REDACTED_TOKEN]"),
        ("password", r"(?i)\b(password|passwd|pwd)\s*[:=]\s*([^\s,;]+)", lambda m: f"{m.group(1)}: [REDACTED_PASSWORD]"),
        ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]"),
        ("phone", r"(?<!\w)(?:\+?\d[\d\s().-]{8,}\d)(?!\w)", "[REDACTED_PHONE]"),
        ("otp", r"(?i)\b(?:otp|code|verification)\D{0,20}(\d{4,8})\b", lambda m: m.group(0).replace(m.group(1), "[REDACTED_OTP]")),
        ("windows_path", r"\b[A-Za-z]:\\Users\\[^\\\s]+\\[^\n\r\t]+", "[LOCAL_WINDOWS_PATH]"),
    ]

    redacted = source
    for kind, pattern, replacement in patterns:
        def repl(match: re.Match[str], *, kind: str = kind, replacement: str | Callable[[re.Match[str]], str] = replacement) -> str:
            events.append(_event(kind, match))
            return replacement(match) if callable(replacement) else replacement

        redacted = re.sub(pattern, repl, redacted, flags=re.DOTALL if kind == "private_key" else 0)
    return redacted, events
