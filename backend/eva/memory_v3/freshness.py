from __future__ import annotations


def classify_freshness(text: str) -> str:
    lowered = str(text or "").lower()
    if "2020" in lowered or "old " in lowered or "stale" in lowered:
        return "stale"
    if "unknown" in lowered:
        return "unknown"
    if "remember that" in lowered or "prefer" in lowered:
        return "fresh"
    return "current"


def freshness_policy_text() -> str:
    from .memory_policy import boundary_lines

    return "\n".join(
        [
            "Memory v3 freshness policy",
            *boundary_lines(),
            "Freshness behavior:",
            "- Current verified project status is preferred over older memory.",
            "- Stale memories are marked stale and excluded from context injection unless safely summarized as blocked metadata.",
            "- Unknown timestamp metadata lowers confidence.",
        ]
    )
