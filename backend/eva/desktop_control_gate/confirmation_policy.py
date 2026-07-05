from __future__ import annotations


def confirmation_policy_text() -> str:
    return "\n".join((
        "Desktop control confirmation policy",
        "Exact confirmation is future-gate metadata only.",
        "Confirmation alone does not execute and cannot enable desktop control.",
    ))
