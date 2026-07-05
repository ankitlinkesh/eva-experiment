from __future__ import annotations

from .collector import collect_control_center_status
from .formatter import format_control_center_status, format_control_center_summary, format_enabled_features, format_locked_features, format_next_safe_step


CONTROL_CENTER_URL = "http://127.0.0.1:8765/control"


def format_control_center_text() -> str:
    return format_control_center_status(collect_control_center_status())


def format_control_center_summary_text() -> str:
    return format_control_center_summary(collect_control_center_status())


def format_locked_features_text() -> str:
    return format_locked_features(collect_control_center_status())


def format_enabled_features_text() -> str:
    return format_enabled_features(collect_control_center_status())


def format_next_safe_step_text() -> str:
    return format_next_safe_step(collect_control_center_status())


def format_control_center_url() -> str:
    return "\n".join(
        [
            "Eva Control Center URL",
            "",
            CONTROL_CENTER_URL,
            "",
            "I did not open a browser. This is a local read-only dashboard URL.",
        ]
    )
