from __future__ import annotations

from .backend_policy import get_backend_policy
from .models import DesktopObservationStatus


def get_desktop_observation_status() -> DesktopObservationStatus:
    backend = get_backend_policy()
    return DesktopObservationStatus(
        status="available",
        mode="explicit one-shot observation-only gate",
        backend_mode=backend.mode,
        backend_available=backend.available,
        mock_fixture_available=True,
        explicit_user_trigger_required=True,
        desktop_control_enabled=False,
        continuous_monitoring_enabled=False,
        screenshot_saving_enabled=False,
        tool_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        arbitrary_file_writes_enabled=False,
        readiness="ready for policy, deterministic mock observation, and unavailable-safe real observation reports",
        next_phase="Phase 26 Real Desktop Control Gate",
    )
