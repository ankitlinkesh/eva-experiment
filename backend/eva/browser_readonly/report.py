from __future__ import annotations

from .models import BrowserObservation
from .observation_policy import boundary_lines


def format_browser_observation(observation: BrowserObservation) -> str:
    links = observation.link_summary or ("none",)
    blocked_notes = observation.blocked_content_notes or ("none",)
    safety_notes = observation.safety_notes or ("none",)
    lines = [
        "Real Browser Read-Only Mode observation",
        *boundary_lines(),
        f"Observation ID: {observation.observation_id}.",
        f"Requested URL: {observation.requested_url or 'not supplied'}.",
        f"Normalized URL: {observation.normalized_url or 'not available'}.",
        f"URL safety decision: {observation.url_safety_decision}",
        f"Backend mode: {observation.backend_mode}.",
        f"Session policy: {observation.session_policy}",
        f"Title preview: {observation.title_preview or 'not available'}.",
        f"Visible text summary: {observation.visible_text_summary or 'not available'}.",
        "Link summary:",
    ]
    lines.extend(f"- {item}" for item in links)
    lines.append("Blocked content notes:")
    lines.extend(f"- {item}" for item in blocked_notes)
    lines.extend(
        [
            f"Redaction status: {observation.redaction_status}.",
            f"Threat scan summary: {observation.threat_scan_summary}",
            f"Execution gate decision: {observation.execution_gate_decision}.",
            f"Final status: {observation.final_status}.",
            f"No-click statement: {observation.no_click_statement}",
            f"No-type statement: {observation.no_type_statement}",
            f"No-form-submit statement: {observation.no_form_submit_statement}",
            f"No-download statement: {observation.no_download_statement}",
            f"No-cookie/session/profile statement: {observation.no_cookie_session_profile_statement}",
            f"No-tool-execution statement: {observation.no_tool_execution_statement}",
            f"No-new-write-path statement: {observation.no_new_write_path_statement}",
            "Safety notes:",
        ]
    )
    lines.extend(f"- {item}" for item in safety_notes)
    return "\n".join(lines)
