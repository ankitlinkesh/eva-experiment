from __future__ import annotations

from .models import ContextBudgetPolicy


_POLICY = ContextBudgetPolicy(
    default_budget_chars=4_000,
    max_budget_chars=8_000,
    section_budget_chars=900,
    oversized_behavior="trim safe low-risk sections or exclude unsafe/noisy sections with reasons",
    safety_priority="safety, grounding, and current project state outrank noisy or stale history",
)


def get_context_budget_policy() -> ContextBudgetPolicy:
    return _POLICY


def trim_to_section_budget(text: str, *, budget_chars: int | None = None) -> tuple[str, bool]:
    limit = int(budget_chars or _POLICY.section_budget_chars)
    clean = str(text or "").strip()
    if len(clean) <= limit:
        return clean, False
    trimmed = clean[: max(0, limit - 40)].rstrip()
    return f"{trimmed} ... [trimmed safely by context budget]", True


def budget_policy_text() -> str:
    return "\n".join(
        [
            "Context Budget Policy",
            "",
            f"Default safe budget: {_POLICY.default_budget_chars} characters.",
            f"Maximum budget: {_POLICY.max_budget_chars} characters.",
            f"Section budget: {_POLICY.section_budget_chars} characters.",
            f"Oversized behavior: {_POLICY.oversized_behavior}.",
            f"Priority: {_POLICY.safety_priority}.",
            "Secrets/config/session data are blocked even if budget remains.",
            "No live LLM call was made. Context assembly is local/mock preview only. Assembled context cannot execute tools.",
        ]
    )
