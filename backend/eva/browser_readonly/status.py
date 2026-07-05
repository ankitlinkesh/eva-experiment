from __future__ import annotations

from .backend_policy import get_backend_policy
from .models import BrowserReadonlyStatus


def get_browser_readonly_status() -> BrowserReadonlyStatus:
    backend = get_backend_policy()
    return BrowserReadonlyStatus(
        status="available",
        mode="public URL read-only observation gate",
        backend_mode=backend.mode,
        backend_available=backend.available,
        mock_fixture_available=True,
        public_urls_only=True,
        sessionless=True,
        credentialless=True,
        browser_control_enabled=False,
        tool_execution_enabled=False,
        arbitrary_file_reads_enabled=False,
        arbitrary_file_writes_enabled=False,
        readiness="ready for URL policy, deterministic mock observation, and unavailable-safe real URL reports",
        next_phase="Phase 25 Real Desktop Observation Mode",
    )
