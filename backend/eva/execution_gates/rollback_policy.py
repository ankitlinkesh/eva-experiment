from __future__ import annotations

from .gate_policy import boundary_lines


def rollback_policy_text() -> str:
    return "\n".join(
        [
            "Controlled Execution Gates rollback policy",
            *boundary_lines(),
            "Rollback behavior:",
            "- Rollback is metadata/preview only for this Phase 20 layer.",
            "- Existing Phase 12L rollback remains the only possible real rollback boundary, and only if that already implemented gate accepts an unchanged Eva-created file.",
            "- Future gates must define their own verified rollback before they can become eligible.",
            "- No rollback preview executes tools or writes files.",
        ]
    )
