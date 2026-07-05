from __future__ import annotations


def build_review_checklist() -> tuple[str, ...]:
    return (
        "Scope matches the stated coding goal and avoids unrelated refactoring.",
        "Existing architecture, interfaces, and compatibility behavior are preserved.",
        "Safety gates, authority rules, privacy boundaries, and write limits remain intact.",
        "Failure paths and human-readable refusals are explicit.",
        "Focused verification covers expected, negative, and regression behavior.",
        "Documentation and handoff notes match the implemented state.",
    )
