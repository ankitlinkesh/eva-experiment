from __future__ import annotations

from .models import ReleaseDemoStatus


def get_release_demo_status() -> ReleaseDemoStatus:
    return ReleaseDemoStatus(
        available=True,
        mode="report/status/demo profile only",
        publishing_enabled=False,
        external_upload_enabled=False,
        git_release_enabled=False,
        readiness="ready for local public-demo review with fresh verifier evidence",
        next_safe_step="user-approved commit execution outside Eva or a separate explicit commit-approval phase",
    )
