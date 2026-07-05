from __future__ import annotations


DEMO_COMMANDS = (
    "eva release status",
    "eva release demo",
    "eva release commands",
    "eva release capability map",
    "eva release safety proof",
    "eva release readiness",
    "eva release limitations",
    "eva release verification",
)


def demo_commands_text() -> str:
    return "\n".join(
        (
            "Eva public demo commands",
            "- Start with `eva release status` for the local profile.",
            "- Use `eva release demo` for the public walkthrough summary.",
            "- Use `eva release capability map` for available and locked surfaces.",
            "- Use `eva release safety proof` for safety-boundary evidence.",
            "- Use `eva release limitations` for honest non-goals.",
            "- Use `eva release verification` for manual verifier commands.",
            "- These commands return text only and perform no external action.",
        )
    )
