from __future__ import annotations

from typing import Any


def verify_page_snapshot(snapshot: dict[str, Any], expected_url: str | None = None, expected_title: str | None = None, expected_text: str | None = None) -> dict[str, Any]:
    url_ok = not expected_url or expected_url.lower() in str(snapshot.get("url", "")).lower()
    title_ok = not expected_title or expected_title.lower() in str(snapshot.get("title", "")).lower()
    text_ok = not expected_text or expected_text.lower() in str(snapshot.get("text", "")).lower()
    verified = bool(snapshot) and url_ok and title_ok and text_ok
    return {
        "ok": True,
        "verified": verified,
        "confidence": 0.8 if verified else 0.35,
        "evidence": "Expected page signals matched." if verified else "Expected page signals were not observed.",
    }
