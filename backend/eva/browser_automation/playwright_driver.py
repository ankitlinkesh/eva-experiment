from __future__ import annotations

from typing import Any

from ..browser.safety import normalize_public_url
from ..runtime.feature_flags import get_v2_feature_flags


def is_playwright_available() -> bool:
    try:
        import playwright  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def playwright_status() -> dict[str, Any]:
    flags = get_v2_feature_flags()
    available = is_playwright_available()
    enabled = bool(flags.playwright_enabled and available)
    return {
        "ok": True,
        "available": available,
        "enabled": enabled,
        "message": "Playwright adapter is optional and disabled unless EVA_V2_PLAYWRIGHT_ENABLED=true.",
        "safety": "No cookie, token, password, or storage reads are exposed by this adapter.",
    }


def _disabled() -> dict[str, Any]:
    return {"ok": False, "error": "playwright_disabled", "message": "Playwright automation is unavailable or disabled; existing Chrome skills remain active."}


def open_url(url: str) -> dict[str, Any]:
    status = playwright_status()
    if not status["enabled"]:
        return _disabled()
    try:
        safe = normalize_public_url(url)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    if not safe:
        return {"ok": False, "error": "unsafe_url"}
    return {"ok": False, "error": "phase1_no_browser_launch", "url": safe, "message": "Phase 1 does not launch Playwright sessions automatically."}


def get_page_snapshot() -> dict[str, Any]:
    return _disabled()


def locate_element(role: str | None = None, name: str | None = None, text: str | None = None) -> dict[str, Any]:
    return {"ok": False, "error": "playwright_disabled", "query": {"role": role, "name": name, "text": text}}


def click_element(target: dict[str, Any]) -> dict[str, Any]:
    return _disabled()


def type_text(target: dict[str, Any], text: str) -> dict[str, Any]:
    return _disabled()


def verify_page(expected_url: str | None = None, expected_title: str | None = None, expected_text: str | None = None) -> dict[str, Any]:
    return {"ok": False, "verified": False, "error": "playwright_disabled", "expected_url": expected_url, "expected_title": expected_title, "expected_text": expected_text}
