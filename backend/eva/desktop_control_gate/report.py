from __future__ import annotations

from .control_policy import BOUNDARY_LINES
from .dry_run import build_desktop_control_dry_run


def desktop_control_report(request: str = "review a desktop action") -> str:
    item = build_desktop_control_dry_run(request)
    return "\n".join((
        "Real Desktop Control Gate report",
        f"Dry-run ID: {item.dry_run_id}",
        f"Action class: {item.action_class}",
        f"Risk: {item.risk_level} ({item.risk_score})",
        f"Gate decision: {item.gate_decision}",
        f"Blocked reason: {item.blocked_reason}",
        *BOUNDARY_LINES,
    ))
