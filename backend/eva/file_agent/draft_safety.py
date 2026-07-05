from __future__ import annotations

import re
from dataclasses import dataclass, field


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.I)),
    ("bearer_token", re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]{12,}", re.I)),
    ("api_key_assignment", re.compile(r"\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{6,}", re.I)),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")),
)

RISKY_PATH_MARKERS = (
    ".env",
    "cookie",
    "cookies",
    "session",
    "localstorage",
    "local storage",
    "login data",
    "browser profile",
    "id_rsa",
    "id_ed25519",
    "private_key",
    "credentials",
    "token",
)

RUNTIME_PATH_MARKERS = (
    "backend/eva/data",
    "backend/data/checkpoints",
    "data/",
    "logs/",
    "traces/",
    "exports/",
    "screenshots/",
)


@dataclass(frozen=True)
class DraftContentSafety:
    allowed: bool
    warnings: list[str] = field(default_factory=list)
    redacted_text: str = ""


def detect_secret_like_text(text: str) -> list[str]:
    found: list[str] = []
    sample = str(text or "")
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(sample):
            found.append(label)
    return _dedupe(found)


def redact_secret_like_text(text: str) -> str:
    output = str(text or "")
    replacements = {
        "private_key": "[REDACTED_PRIVATE_KEY]",
        "bearer_token": "[REDACTED_TOKEN]",
        "api_key_assignment": "[REDACTED_SECRET_ASSIGNMENT]",
        "github_token": "[REDACTED_TOKEN]",
        "openai_key": "[REDACTED_API_KEY]",
    }
    for label, pattern in SECRET_PATTERNS:
        output = pattern.sub(replacements[label], output)
    return output


def detect_risky_draft_path(path_text: str) -> list[str]:
    normalized = str(path_text or "").replace("\\", "/").lower()
    warnings = [marker for marker in RISKY_PATH_MARKERS if marker in normalized]
    warnings.extend(marker.rstrip("/") for marker in RUNTIME_PATH_MARKERS if normalized.startswith(marker) or f"/{marker}" in normalized)
    return _dedupe(warnings)


def validate_proposed_file_content(path_text: str, content: str) -> DraftContentSafety:
    warnings: list[str] = []
    path_warnings = detect_risky_draft_path(path_text)
    if path_warnings:
        warnings.append("Draft target looks sensitive or runtime-only.")
    secret_hits = detect_secret_like_text(content)
    if secret_hits:
        warnings.append("Draft content contains secret-like text and was redacted in the preview.")
    if len(str(content or "")) > 200_000:
        warnings.append("Draft content is too large for FileAgent preview mode.")
    if _looks_binary(content):
        warnings.append("Draft content looks binary and is not suitable for text preview mode.")
    allowed = not path_warnings and not secret_hits and "too large" not in " ".join(warnings).lower() and "binary" not in " ".join(warnings).lower()
    return DraftContentSafety(allowed=allowed, warnings=_dedupe(warnings), redacted_text=redact_secret_like_text(content))


def format_draft_safety_review(result: DraftContentSafety) -> str:
    lines = ["Draft safety review", "", f"Status: {'allowed for preview' if result.allowed else 'blocked or warning'}."]
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    else:
        lines.append("Warnings: none.")
    lines.append("")
    lines.append("Scope: preview only. No file was created or modified.")
    return "\n".join(lines)


def _looks_binary(text: str) -> bool:
    sample = str(text or "")[:2000]
    if "\x00" in sample:
        return True
    return False


def _dedupe(items: list[str]) -> list[str]:
    output: list[str] = []
    for item in items:
        if item and item not in output:
            output.append(item)
    return output
