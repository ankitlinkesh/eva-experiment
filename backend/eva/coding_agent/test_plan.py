from __future__ import annotations


def build_test_plan_preview() -> tuple[str, ...]:
    return (
        "Run the focused verifier for the affected behavior manually.",
        "Exercise deterministic positive and negative cases.",
        "Confirm unsafe or unsupported requests fail closed.",
        "Run the relevant quick regression profile manually.",
        "Run the full regression profile before declaring the phase complete.",
        "Check compilation, diff integrity, and the final working-tree status.",
    )
