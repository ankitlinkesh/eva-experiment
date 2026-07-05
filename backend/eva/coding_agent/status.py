from __future__ import annotations

from .models import CodingStatus


def get_coding_status() -> CodingStatus:
    return CodingStatus(
        available=True,
        mode="preview/report/status only",
        source_editing_enabled=False,
        patch_application_enabled=False,
        execution_enabled=False,
        readiness="Phase 28 foundation ready for deterministic local previews",
        next_phase="Phase 29 Public Demo / Release",
    )
