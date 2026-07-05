from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


MAX_STRUCTURED_OUTPUT_CHARS = 12_000
_SECRET_PATTERN = re.compile(
    r"(?:\b(?:api[_-]?key|secret|token|password|cookie|authorization)\b\s*[:=]\s*\S+|\bsk-[A-Za-z0-9_-]{8,}|\bAIza[0-9A-Za-z_-]{12,}|\bBearer\s+[A-Za-z0-9._~+/-]{8,})",
    re.IGNORECASE,
)
_PRIVATE_PATH_PATTERN = re.compile(
    r"(?:\b[A-Za-z]:\\Users\\|(?:^|\s)/Users/|(?:^|\s)/home/|~/(?:\.ssh|\.aws|\.config|AppData)/|%USERPROFILE%)",
    re.IGNORECASE,
)
_CAPABILITY_CLAIM_PATTERN = re.compile(r"\bcapability\s+([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)\b", re.IGNORECASE)
_EXECUTION_FIELD_MARKERS = ("tool", "execute", "command", "shell", "browser", "desktop", "pyautogui", "playwright", "mcp")
_EXECUTION_TEXT_MARKERS = ("tool_call", "execute_tool", "run_shell", "browser.execute", "desktop.execute", "pyautogui", "playwright", "mcp.call")


def validation_policy_text() -> str:
    return "Mock-only validation rejects malformed, oversized, secret-like, private-path, unknown-capability, and execution-request output. Invalid output cannot execute tools."


def collect_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(f"{key} {collect_text(item)}" for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return " ".join(collect_text(item) for item in value)
    return str(value) if value is not None else ""


def is_secret_like_output(value: object) -> bool:
    return bool(_SECRET_PATTERN.search(collect_text(value)))


def is_private_path_like_output(value: object) -> bool:
    return bool(_PRIVATE_PATH_PATTERN.search(collect_text(value)))


def find_capability_claims(value: object) -> tuple[str, ...]:
    return tuple(match.group(1).lower() for match in _CAPABILITY_CLAIM_PATTERN.finditer(collect_text(value)))


def requests_execution(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key).lower()
            if any(marker in key_text for marker in _EXECUTION_FIELD_MARKERS):
                return True
            if requests_execution(item):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(requests_execution(item) for item in value)
    if isinstance(value, str):
        text = value.lower()
        return any(marker in text for marker in _EXECUTION_TEXT_MARKERS)
    return False
