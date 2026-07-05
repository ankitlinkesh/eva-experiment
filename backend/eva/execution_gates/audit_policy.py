from __future__ import annotations

from .gate_policy import boundary_lines


def audit_policy_text() -> str:
    return "\n".join(
        [
            "Controlled Execution Gates audit policy",
            *boundary_lines(),
            "Audit behavior:",
            "- Phase 20 emits deterministic local report metadata only.",
            "- A future executor must record action class, decision state, approval requirement, confirmation requirement, rollback availability, and blocked reason before any eligible gate can run.",
            "- Raw WorkSession/private runtime dumps are denied and are not exposed in user-facing reports.",
            "- This policy does not add a database write, tool call, browser action, desktop action, shell step, cloud call, or MCP action.",
        ]
    )
