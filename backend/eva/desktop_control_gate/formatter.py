from __future__ import annotations

from .action_catalog import format_action_catalog
from .approval_policy import approval_policy_text
from .confirmation_policy import confirmation_policy_text
from .control_policy import BOUNDARY_LINES, control_policy_text
from .dry_run import build_desktop_control_dry_run
from .status import get_desktop_control_gate_status


def _with_boundaries(title: str, body: str) -> str:
    return "\n".join((title, body, "", *BOUNDARY_LINES))


def format_desktop_control_status() -> str:
    status = get_desktop_control_gate_status()
    return _with_boundaries("Real Desktop Control Gate status", f"Status: available\nMode: {status.mode}\nReadiness: {status.readiness}\nNext phase: {status.next_phase}")


def format_desktop_control_policy() -> str:
    return _with_boundaries("Real Desktop Control Gate policy", control_policy_text())


def format_desktop_control_actions() -> str:
    return _with_boundaries("Real Desktop Control Gate actions", format_action_catalog())


def format_desktop_control_dry_run(request: str = "review a desktop action") -> str:
    item = build_desktop_control_dry_run(request)
    body = "\n".join((
        f"Dry-run ID: {item.dry_run_id}",
        f"Requested action: {item.requested_action_summary}",
        f"Action class: {item.action_class}",
        f"Risk: {item.risk_level} ({item.risk_score})",
        f"Gate decision: {item.gate_decision}",
        f"Approval: {item.approval_requirement}",
        f"Confirmation: {item.exact_confirmation_requirement}",
        f"Rollback: {item.rollback_metadata}",
        f"Audit: {item.audit_metadata}",
        f"Result: {item.final_status}",
    ))
    return _with_boundaries("Real Desktop Control Gate dry run", body)


def format_desktop_control_approvals() -> str:
    return _with_boundaries("Real Desktop Control Gate approvals", approval_policy_text())


def format_desktop_control_confirmations() -> str:
    return _with_boundaries("Real Desktop Control Gate confirmations", confirmation_policy_text())


def format_desktop_control_blocked_actions() -> str:
    return _with_boundaries(
        "Real Desktop Control Gate blocked actions",
        "Always blocked: secrets/credentials/sessions/cookies, destructive actions, shell, package, cloud, MCP, browser control, file writes, and unknown capabilities.",
    )


def format_desktop_control_readiness() -> str:
    return _with_boundaries(
        "Real Desktop Control Gate readiness",
        "Phase 26 is complete as a deterministic local/mock policy and dry-run gate. No desktop-control executor exists.\nNext phase: Phase 27 News/Web Intelligence Dashboard.",
    )
