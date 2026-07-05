from __future__ import annotations

import re

from .models import ThreatFinding


_SECRET_MARKERS = ("api key", "apikey", "secret", "environment file", ".env", "config secret", "token", "cookie", "password", "private key")
_SESSION_MARKERS = ("browser session", "session cookies", "cookies", "localstorage", "profile data")
_PRIVATE_PATH = re.compile(r"\b[A-Za-z]:\\Users\\[^ \n\r\t,;]+", re.IGNORECASE)


def detect_exfiltration(text: str, source_type: str) -> tuple[ThreatFinding, ...]:
    lowered = str(text or "").lower()
    findings: list[ThreatFinding] = []
    if any(marker in lowered for marker in _SECRET_MARKERS):
        findings.append(_finding("secret_exfiltration", "critical", source_type, "Secret/config/token/cookie/password-like access was requested."))
    if any(marker in lowered for marker in _SESSION_MARKERS):
        findings.append(_finding("browser_session_exfiltration", "critical", source_type, "Browser-session-like data access was requested."))
    if _PRIVATE_PATH.search(str(text or "")):
        findings.append(_finding("private_path_exfiltration", "high", source_type, "Private-path-looking text was redacted and blocked."))
    return tuple(findings)


def _finding(category: str, severity: str, source_type: str, summary: str) -> ThreatFinding:
    return ThreatFinding(category, severity, source_type, summary, "block_exfiltration")
