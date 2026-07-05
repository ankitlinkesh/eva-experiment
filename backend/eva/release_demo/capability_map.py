from __future__ import annotations


CAPABILITY_MAP = (
    "Deterministic command system: local routing and human-readable status.",
    "Planner and agent loop: bounded preview/planning with stop and safety gates.",
    "Capability registry: cataloged permissions, resources, schemas, and verifier metadata.",
    "Browser: public-URL read-only observation only; browser control is locked.",
    "Desktop: one-shot observation only; control remains dry-run/gate-only.",
    "News: local/mock or safe public-URL read-only reports only.",
    "CodingAgent: classification, plans, reviews, tests, risk, and handoff previews only.",
    "Voice: locked/mock foundation only; no microphone, audio, ASR, or TTS runtime.",
    "Real writes: Phase 12L narrow approved new Markdown/text creation only.",
)


def capability_map_text() -> str:
    return "\n".join(("Eva public capability map", *[f"- {item}" for item in CAPABILITY_MAP]))
