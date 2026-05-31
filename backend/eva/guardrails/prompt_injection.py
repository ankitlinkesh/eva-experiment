from __future__ import annotations


INJECTION_MARKERS = (
    "ignore previous instructions",
    "reveal system prompt",
    "exfiltrate",
    "send secrets",
    "bypass safety",
    "disable safety",
    "developer message",
)


def detect_prompt_injection(text: str) -> dict[str, object]:
    lowered = str(text or "").lower()
    found = [marker for marker in INJECTION_MARKERS if marker in lowered]
    return {
        "blocked": bool(found),
        "warnings": ["prompt_injection_phrase"] if found else [],
        "matches": found,
        "reason": "Prompt injection phrase detected." if found else "",
    }
