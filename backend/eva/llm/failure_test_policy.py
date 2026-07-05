from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailureTestPolicy:
    mode: str
    live_calls_allowed: bool
    tool_execution_allowed: bool
    secret_reads_allowed: bool
    summary: str


def get_failure_test_policy() -> FailureTestPolicy:
    return FailureTestPolicy("local/mock only", False, False, False, "Unsafe LLM-like output is classified, blocked, and reported without execution.")


def is_policy_unsafe(category: str) -> bool:
    return category in {"prompt_injection", "ignore_safety", "config_secret_request", "browser_session", "nested_suspicious_payload", "command_injection", "blocked_action_attempt"}
