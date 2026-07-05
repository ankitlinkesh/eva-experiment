from __future__ import annotations

from dataclasses import dataclass

from .output_contracts import StructuredOutputValidationResult


@dataclass(frozen=True)
class SafeRepairPlan:
    """Instructions only: no retry, tool call, output rewrite, or execution path."""

    execute: bool
    user_intent: str
    repaired_output: None
    instructions: tuple[str, ...]


def plan_safe_repair(result: StructuredOutputValidationResult, *, user_intent: str) -> SafeRepairPlan:
    """Preserve the original intent while describing a non-executing repair option."""
    issues = ", ".join(result.issues) or "validation_failed"
    return SafeRepairPlan(
        execute=False,
        user_intent=user_intent,
        repaired_output=None,
        instructions=(
            "Do not execute tools, browser actions, desktop actions, shell commands, or network calls.",
            "Do not alter the user's intent.",
            f"Ask for a fresh schema-valid preview after resolving: {issues}.",
        ),
    )
