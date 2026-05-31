from __future__ import annotations

from typing import Any


def verify_desktop_target(observation: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    title = str(observation.get("active_window_title") or "").lower()
    expected_title = str(expected.get("title") or "").lower()
    verified = bool(expected_title and expected_title in title)
    return {
        "ok": True,
        "verified": verified,
        "confidence": 0.8 if verified else 0.35,
        "evidence": "Expected active window title matched." if verified else "Expected desktop target was not observed.",
    }
