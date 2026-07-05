from __future__ import annotations


def approval_policy_text() -> str:
    return "\n".join((
        "Desktop control approval policy",
        "Approval is future-gate metadata only.",
        "Approval alone does not execute and cannot enable desktop control.",
    ))
