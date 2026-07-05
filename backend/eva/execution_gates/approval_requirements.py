from __future__ import annotations

from .gate_policy import boundary_lines


def approval_policy_text() -> str:
    return "\n".join(
        [
            "Controlled Execution Gates approval policy",
            *boundary_lines(),
            "Approval behavior:",
            "- Status/report/preview actions do not require approval because they do not execute.",
            "- Existing Phase 12L real-create candidates still require the already implemented approval metadata before that existing gate can consider them.",
            "- Future gates may require explicit approval later, but they are locked candidates now.",
            "- Approval alone does not execute anything and does not create a new write path.",
        ]
    )
