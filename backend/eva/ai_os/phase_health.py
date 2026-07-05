from __future__ import annotations

from .models import PhaseHealthEntry
from .safety_boundaries import boundary_lines


def build_phase_health() -> tuple[PhaseHealthEntry, ...]:
    phases = (
        ("Phase 12", "FileAgent safety gates", "verified in latest known master metadata"),
        ("Phase 13", "BrowserAgent safety foundation", "verified safety foundation"),
        ("Phase 14", "DesktopAgent safety foundation", "verified and locked"),
        ("Phase 15", "LLM safety spine", "verified local/mock"),
        ("Phase 16", "Context assembly", "verified local/mock"),
        ("Phase 17", "Threat defense", "verified local/mock"),
        ("Phase 18", "Agent loop v1", "verified preview-only"),
        ("Phase 19", "Workflow planner", "verified preview-only"),
        ("Phase 20", "Controlled execution gates", "verified policy-preview only"),
        ("Phase 21", "Memory v3", "verified local-only"),
        ("Phase 22", "Voice Assistant Foundation", "verified local/mock"),
        ("Phase 23", "AI OS / Control Center Upgrade", "verified local/status only"),
        ("Phase 24", "Real Browser Read-Only Mode", "verified public-URL observation only; browser control locked"),
        ("Phase 25", "Real Desktop Observation Mode", "verified one-shot observation only; desktop control locked"),
        ("Phase 26", "Real Desktop Control Gate", "verified local/mock dry-run gate only; no desktop-control executor"),
    )
    return tuple(
        PhaseHealthEntry(phase, feature, health, "known local status metadata", "No verifier was started by dashboard rendering.")
        for phase, feature, health in phases
    )


def phase_health_text() -> str:
    lines = [
        "AI OS phase health",
        *boundary_lines(),
        "Health summarizes known local metadata; it does not run verifiers automatically.",
    ]
    lines.extend(f"- {item.phase} {item.feature_name}: {item.health}." for item in build_phase_health())
    return "\n".join(lines)
