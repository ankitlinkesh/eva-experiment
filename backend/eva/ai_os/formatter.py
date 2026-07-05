from __future__ import annotations

from .capability_matrix import capability_matrix_text
from .feature_states import feature_states_text, locked_features_text
from .next_steps import next_safe_step_text
from .phase_health import phase_health_text
from .readiness import build_ai_os_dashboard, readiness_text
from .safety_boundaries import boundary_lines, safety_boundaries_text
from .status import get_ai_os_status
from .system_map import system_map_text


def format_ai_os_status() -> str:
    status = get_ai_os_status()
    return "\n".join(
        [
            "Eva AI OS status",
            *boundary_lines(),
            f"Status: {status.status}.",
            f"Mode: {status.mode}.",
            f"Current phase: {status.current_phase}.",
            f"Overall readiness: {status.overall_readiness}.",
            f"Web server enabled: {status.web_server_enabled}.",
            f"Browser launch enabled: {status.browser_launch_enabled}.",
            f"Desktop UI enabled: {status.desktop_ui_enabled}.",
            f"Background daemon enabled: {status.background_daemon_enabled}.",
            f"Next phase: {status.next_phase}.",
        ]
    )


def format_ai_os_dashboard() -> str:
    return build_ai_os_dashboard().format()


def format_ai_os_system_map() -> str:
    return system_map_text()


def format_ai_os_capability_matrix() -> str:
    return capability_matrix_text()


def format_ai_os_feature_states() -> str:
    return feature_states_text()


def format_ai_os_safety_boundaries() -> str:
    return safety_boundaries_text()


def format_ai_os_locked_features() -> str:
    return locked_features_text()


def format_ai_os_next_safe_step() -> str:
    return next_safe_step_text()


def format_ai_os_readiness() -> str:
    return readiness_text()
