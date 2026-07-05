from __future__ import annotations

from .gate_policy import boundary_lines


def confirmation_policy_text() -> str:
    return "\n".join(
        [
            "Controlled Execution Gates confirmation policy",
            *boundary_lines(),
            "Confirmation behavior:",
            "- Preview/report/status commands do not need a confirmation phrase.",
            "- Confirmation alone does not execute unless an existing implemented gate accepts it.",
            "- The only existing implemented real write confirmation boundary is Phase 12L narrow real-create for approved new .md/.txt files.",
            "- Future confirmation phrases are described as locked policy metadata only.",
        ]
    )
