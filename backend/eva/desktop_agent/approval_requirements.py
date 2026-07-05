from __future__ import annotations

from .risk_scoring import DesktopApprovalLevel, DesktopApprovalRequirement, score_desktop_action_risk


def determine_desktop_approval_requirement(request: str) -> DesktopApprovalRequirement:
    return score_desktop_action_risk(request).approval


def list_desktop_approval_levels() -> tuple[DesktopApprovalLevel, ...]:
    return tuple(DesktopApprovalLevel)
