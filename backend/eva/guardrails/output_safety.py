from __future__ import annotations


UNSAFE_OUTPUT_MARKERS = (
    "steal password",
    "dump credentials",
    "malware persistence",
    "hidden monitoring",
)


def detect_unsafe_output(text: str) -> dict[str, object]:
    lowered = str(text or "").lower()
    found = [marker for marker in UNSAFE_OUTPUT_MARKERS if marker in lowered]
    return {
        "blocked": bool(found),
        "warnings": ["unsafe_output_phrase"] if found else [],
        "matches": found,
        "reason": "Unsafe output phrase detected." if found else "",
    }
