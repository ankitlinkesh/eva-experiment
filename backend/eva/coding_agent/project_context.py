from __future__ import annotations

from .models import ProjectContextSummary


def build_project_context_summary() -> ProjectContextSummary:
    return ProjectContextSummary(
        summary=(
            "Eva is represented through pre-existing architecture, phase-status, capability, "
            "safety-boundary, and verification metadata. No repository file body was opened "
            "or returned by the CodingAgent."
        ),
        sources=(
            "Eva current-state status metadata",
            "Eva capability and safety metadata",
            "Eva planner and verifier status metadata",
            "Explicit future FileAgent workflow metadata when separately approved",
        ),
        policy=(
            "Safe project context uses existing metadata/status/docs summaries only. "
            "Arbitrary filesystem access and raw code output are not available."
        ),
    )
