from __future__ import annotations

from .safety_boundaries import boundary_lines


def next_safe_step_text() -> str:
    return "\n".join(
        [
            "AI OS next safe step",
            *boundary_lines(),
            "Recommended next phase: Phase 27 News/Web Intelligence Dashboard.",
            "Phase 25 desktop observation remains explicit, one-shot, redaction-first, and control-locked.",
            "Phase 26 desktop control remains a local/mock dry-run gate with no executor.",
            "The dashboard recommendation is metadata only and starts no work automatically.",
        ]
    )
