from __future__ import annotations


def build_handoff_notes(task_type: str, specialist_mode: str) -> tuple[str, ...]:
    return (
        f"Classified task: {task_type}.",
        f"Selected specialist mode: {specialist_mode}.",
        "Review the proposed plan and verification recommendations before implementation.",
        "Use a separately authorized development workflow for any future source change.",
        "Keep Phase 12L as Eva's only existing real file-write boundary.",
    )
