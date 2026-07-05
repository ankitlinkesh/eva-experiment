from __future__ import annotations

import re


_SECRET_ASSIGNMENT = re.compile(
    r"\b(?:api[_-]?(?:key|token)|token|cookie|password|passwd|session|secret|bearer)\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)
_WINDOWS_PRIVATE_PATH = re.compile(r"\b[A-Za-z]:\\Users\\[^ \n\r\t,;]+", re.IGNORECASE)
_UNIX_PRIVATE_PATH = re.compile(r"(?<!\w)/(?:home|Users)/[^ \n\r\t,;]+", re.IGNORECASE)
_CONFIG_NAME = re.compile(r"(?<![\w.-])\.env(?:\.local)?(?![\w.-])", re.IGNORECASE)


def redact_browser_output(value: object) -> str:
    text = str(value or "")
    text = _SECRET_ASSIGNMENT.sub("[redacted secret-like value]", text)
    text = _WINDOWS_PRIVATE_PATH.sub("[redacted private path]", text)
    text = _UNIX_PRIVATE_PATH.sub("[redacted private path]", text)
    text = _CONFIG_NAME.sub("[blocked config file]", text)
    return text


def summarize_visible_text(value: object, *, limit: int = 720) -> str:
    redacted = redact_browser_output(value)
    compact = " ".join(redacted.split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 14)].rstrip() + " ... [trimmed]"


def redaction_policy_text() -> str:
    return "\n".join(
        [
            "Browser observation redaction policy",
            "Secret-like assignments, cookies, passwords, sessions, tokens, private user paths, and config filenames are redacted.",
            "Visible text and link labels are whitespace-normalized and length-limited.",
            "Raw page content is not returned.",
        ]
    )
