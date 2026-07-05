from __future__ import annotations


def detect_conflict(text: str) -> tuple[str, str]:
    lowered = str(text or "").lower()
    if "complete but" in lowered or "failed" in lowered or "conflict" in lowered:
        return "conflict_reported", "Conflicting memory is reported and excluded until current evidence resolves it."
    return "no_conflict_detected", ""


def conflict_policy_text() -> str:
    from .memory_policy import boundary_lines

    return "\n".join(
        [
            "Memory v3 conflict detection",
            *boundary_lines(),
            "Conflict behavior:",
            "- Conflicting memories are reported, not merged blindly.",
            "- Current verified project status is preferred over older memory.",
            "- Conflict records are excluded from context injection until grounded.",
        ]
    )
