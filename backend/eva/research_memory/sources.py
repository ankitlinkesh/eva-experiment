from __future__ import annotations

import re
from urllib.parse import urlparse

from .config import MAX_NOTE_LENGTH, MAX_TAGS, MAX_URL_LENGTH


TOKEN_RE = re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")
ENV_RE = re.compile(r"(?im)^\s*[A-Z0-9_]{3,}\s*=\s*.+$")
PASSWORD_RE = re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*['\"]?[^'\"\s]{4,}")
BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{10,}")
API_KEY_RE = re.compile(r"\b(sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{12,}|ghp_[0-9A-Za-z]{12,}|github_pat_[0-9A-Za-z_]{12,})\b")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL)
STORAGE_RE = re.compile(r"(?i)\b(cookie|localStorage|sessionStorage|document\.cookie)\b")


def extract_domain(url: str | None) -> str | None:
    normalized = normalize_source_url(url)
    if not normalized:
        return None
    parsed = urlparse(normalized)
    return parsed.netloc.lower() or None


def normalize_source_url(url: str | None) -> str | None:
    text = str(url or "").strip()
    if not text:
        return None
    if len(text) > MAX_URL_LENGTH:
        text = text[:MAX_URL_LENGTH]
    lowered = text.lower()
    if lowered.startswith(("javascript:", "file:", "data:", "chrome:", "about:")):
        return None
    if not lowered.startswith(("http://", "https://")):
        return None
    return text


def looks_private_or_sensitive(text: str) -> bool:
    value = str(text or "")
    lowered = value.lower()
    if any(marker in lowered for marker in (".env", "private key", "password", "bearer ", "cookie", "localstorage", "sessionstorage", "logged-in", "logged in", "gmail", "whatsapp chat")):
        return True
    return bool(API_KEY_RE.search(value) or BEARER_RE.search(value) or PASSWORD_RE.search(value) or PRIVATE_KEY_RE.search(value) or ENV_RE.search(value) or STORAGE_RE.search(value))


def redact_research_text(text: str, max_len: int | None = None) -> tuple[str, bool]:
    value = str(text or "").replace("\x00", "").strip()
    heavy_secret = bool(PRIVATE_KEY_RE.search(value) or ENV_RE.search(value) or STORAGE_RE.search(value))
    redacted = PRIVATE_KEY_RE.sub("[REDACTED_PRIVATE_KEY]", value)
    redacted = ENV_RE.sub("[REDACTED_ENV_LINE]", redacted)
    redacted = API_KEY_RE.sub("[REDACTED_API_KEY]", redacted)
    redacted = BEARER_RE.sub("[REDACTED_TOKEN]", redacted)
    redacted = PASSWORD_RE.sub("[REDACTED_PASSWORD]", redacted)
    redacted = STORAGE_RE.sub("[REDACTED_BROWSER_STORAGE]", redacted)
    redacted = TOKEN_RE.sub("[REDACTED_TOKEN]", redacted)
    changed = redacted != value
    limit = max_len if max_len is not None else MAX_NOTE_LENGTH
    if heavy_secret:
        return "Sensitive/private research content was withheld locally; only this redacted warning was saved.", True
    if len(redacted) > limit:
        redacted = redacted[:limit].rstrip()
    return redacted, changed


def infer_topic(text: str) -> str:
    words = [part for part in re.split(r"[^A-Za-z0-9+#.-]+", str(text or "")) if len(part) > 2]
    if not words:
        return "general"
    return " ".join(words[:4])[:120]


def extract_tags(text: str, limit: int = MAX_TAGS) -> list[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "into", "about", "research", "memory", "note"}
    seen: list[str] = []
    for word in re.split(r"[^A-Za-z0-9+#.-]+", str(text or "").lower()):
        if len(word) < 3 or word in stop or word in seen:
            continue
        seen.append(word[:40])
        if len(seen) >= max(1, min(MAX_TAGS, int(limit or MAX_TAGS))):
            break
    return seen
