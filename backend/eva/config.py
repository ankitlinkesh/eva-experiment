from __future__ import annotations

from copy import deepcopy
from typing import Any


HYBRID_DEFAULTS: dict[str, dict[str, Any]] = {
    "privacy": {
        "memory_storage": "local",
        "cloud_llm_allowed": True,
        "send_private_context_to_cloud": "ask",
        "redact_secrets_before_cloud": True,
        "cloud_context_mode": "minimal",
        "raw_screenshot_to_cloud": "ask",
        "raw_file_to_cloud": "ask",
        "raw_chat_to_cloud": "ask",
        "behavior_learning": "ask_before_save",
    },
    "agent": {
        "max_steps": 8,
        "max_repairs": 2,
        "require_verification": True,
        "rollback_enabled": True,
        "checkpoint_before_risky_action": True,
        "stop_on_uncertain_state": True,
    },
    "screen": {
        "enabled": True,
        "always_on_watch": False,
        "observe_only_on_task": True,
        "capture_interval_ms": 0,
        "require_permission_for_private_windows": True,
        "require_permission_for_screen_reading": True,
    },
    "override": {
        "enabled": True,
        "phrase": "confirm override",
        "expires_after_seconds": 120,
        "log_overrides": True,
    },
    "actions": {
        "message_send_requires_confirmation": True,
        "posting_requires_confirmation": True,
        "file_delete_requires_override": True,
        "system_change_requires_override": True,
        "power_action_requires_confirmation": True,
        "shell_default": "blocked",
    },
}


def hybrid_defaults() -> dict[str, dict[str, Any]]:
    return deepcopy(HYBRID_DEFAULTS)
