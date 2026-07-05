from __future__ import annotations

from .models import DesktopObservation
from .observation_policy import boundary_lines


def format_desktop_observation(observation: DesktopObservation) -> str:
    metadata = observation.app_window_metadata_preview or ("none",)
    blocked_notes = observation.blocked_content_notes or ("none",)
    safety_notes = observation.safety_notes or ("none",)
    lines = [
        "Real Desktop Observation Mode observation",
        *boundary_lines(),
        f"Observation ID: {observation.observation_id}.",
        f"Requested observation type: {observation.requested_observation_type}.",
        f"Backend mode: {observation.backend_mode}.",
        f"Capture gate decision: {observation.capture_gate_decision}.",
        f"Sensitive screen classification: {observation.sensitive_screen_classification}.",
        f"Redaction status: {observation.redaction_status}.",
        f"Visible summary preview: {observation.visible_summary_preview or 'not available'}.",
        "App/window metadata preview:",
    ]
    lines.extend(f"- {item}" for item in metadata)
    lines.append("Blocked content notes:")
    lines.extend(f"- {item}" for item in blocked_notes)
    lines.extend(
        [
            f"Threat scan summary: {observation.threat_scan_summary}",
            f"Execution gate decision: {observation.execution_gate_decision}.",
            f"Final status: {observation.final_status}.",
            f"No-click statement: {observation.no_click_statement}",
            f"No-type statement: {observation.no_type_statement}",
            f"No-hotkey statement: {observation.no_hotkey_statement}",
            f"No-app-control statement: {observation.no_app_control_statement}",
            f"No-continuous-monitoring statement: {observation.no_continuous_monitoring_statement}",
            f"No-screenshot-save statement: {observation.no_screenshot_save_statement}",
            f"No-cookie/session/profile statement: {observation.no_cookie_session_profile_statement}",
            f"No-tool-execution statement: {observation.no_tool_execution_statement}",
            f"No-new-write-path statement: {observation.no_new_write_path_statement}",
            "Safety notes:",
        ]
    )
    lines.extend(f"- {item}" for item in safety_notes)
    return "\n".join(lines)
