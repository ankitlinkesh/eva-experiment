from __future__ import annotations

from .models import ReleaseCandidateStatus


def get_release_candidate_status() -> ReleaseCandidateStatus:
    return ReleaseCandidateStatus(
        available=True,
        mode="report/status/planning only",
        git_operations_enabled=False,
        publishing_enabled=False,
        runtime_execution_enabled=False,
        readiness="ready for user review after fresh verifier evidence",
        next_safe_step="user-approved commit execution outside Eva or a separate explicit commit-approval phase",
    )
