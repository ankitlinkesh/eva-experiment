from __future__ import annotations

import re

from .observation_policy import boundary_lines


_SECRET_ASSIGNMENT = re.compile(
    r"\b(?:api[_-]?(?:key|token)|token|cookie|password|passwd|session|secret|bearer)\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)
_WINDOWS_PRIVATE_PATH = re.compile(r"\b[A-Za-z]:\\Users\\[^ \n\r\t,;]+", re.IGNORECASE)
_UNIX_PRIVATE_PATH = re.compile(r"(?<!\w)/(?:home|Users)/[^ \n\r\t,;]+", re.IGNORECASE)
_CONFIG_NAME = re.compile(r"(?<![\w.-])\.env(?:\.local)?(?![\w.-])", re.IGNORECASE)


def redact_desktop_output(value: object) -> str:
    text = str(value or "")
    text = _SECRET_ASSIGNMENT.sub("[redacted secret-like value]", text)
    text = _WINDOWS_PRIVATE_PATH.sub("[redacted private path]", text)
    text = _UNIX_PRIVATE_PATH.sub("[redacted private path]", text)
    text = _CONFIG_NAME.sub("[blocked config file]", text)
    return text


def summarize_visible_content(value: object, *, limit: int = 720) -> str:
    compact = " ".join(redact_desktop_output(value).split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 14)].rstrip() + " ... [trimmed]"


def redaction_policy_text() -> str:
    return "\n".join(
        [
            "Real Desktop Observation Mode redaction policy",
            *boundary_lines(),
            "Secret-like assignments, cookies, passwords, sessions, tokens, private user paths, and config filenames are redacted.",
            "Visible summaries and app/window metadata are whitespace-normalized and length-limited.",
            "Sensitive screens may be summarized only after classification and redaction.",
            "Raw screen pixels, raw OCR, and private screen dumps are never returned or saved.",
        ]
    )
