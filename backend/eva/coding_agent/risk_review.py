from __future__ import annotations

from .coding_policy import blocked_actions_text
from .models import CodingClassification


def build_risk_review(classification: CodingClassification) -> tuple[tuple[str, ...], tuple[str, ...]]:
    risks = (
        "Execution risk: controlled by preview-only output and the absence of an executor.",
        "Privacy risk: controlled by metadata-only context and blocked secret/session access.",
        "Mutation risk: controlled by blocked arbitrary reads/writes and patch application.",
        "Hallucination risk: unknown capabilities are rejected instead of being invented.",
    )
    blocked = tuple(blocked_actions_text().splitlines()[1:])
    if classification.blocked:
        blocked = (
            f"Request refused: {classification.reason}",
            *blocked,
        )
    return risks, blocked
