from __future__ import annotations

from .models import DesktopControlGateStatus


def get_desktop_control_gate_status() -> DesktopControlGateStatus:
    return DesktopControlGateStatus(
        available=True,
        mode="local/mock dry-run gate only",
        real_control_enabled=False,
        observation_mode="Phase 25 remains available_observation_only",
        readiness="complete as policy/dry-run gate; no executor exists",
        next_phase="Phase 27 News/Web Intelligence Dashboard",
    )
