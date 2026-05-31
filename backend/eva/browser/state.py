from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


CURRENT_PAGE_CACHE_TTL_SECONDS = 45


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class BrowserObservation:
    timestamp: str
    browser_detected: bool
    active_window_title: str | None = None
    current_url: str | None = None
    current_title: str | None = None
    source: str = "unknown"
    verified: bool = False
    stale: bool = True
    captured_at: str | None = None
    age_seconds: float | None = None
    message: str = ""
    tabs: list[dict[str, Any]] = field(default_factory=list)
    page_summary: str | None = None
    extracted_links: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_STATE: dict[str, Any] = {
    "last_url": None,
    "last_title": None,
    "url": None,
    "title": None,
    "source": "unknown",
    "verified": False,
    "stale": True,
    "captured_at": None,
    "message": "No browser page has been verified yet.",
    "last_search_query": None,
    "last_search_url": None,
    "last_results": [],
    "updated_at": None,
}


def _age_seconds(captured_at: str | None) -> float | None:
    parsed = _parse_time(captured_at)
    if parsed is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def _remember_page_state(url: str | None, title: str | None, *, source: str, verified: bool, message: str = "") -> None:
    captured_at = _now()
    _STATE["last_url"] = url
    _STATE["url"] = url
    if title:
        _STATE["last_title"] = title
        _STATE["title"] = title
    _STATE["source"] = source
    _STATE["verified"] = bool(verified)
    _STATE["stale"] = not bool(verified)
    _STATE["captured_at"] = captured_at
    _STATE["updated_at"] = captured_at
    _STATE["message"] = message or ("Current page verified from live Chrome." if verified else "Last known page is cached and unverified.")


def remember_navigation(url: str, title: str | None = None, *, source: str = "cache", verified: bool = False) -> None:
    _STATE["last_url"] = url
    _remember_page_state(url, title, source=source, verified=verified)


def remember_live_probe(url: str, title: str | None = None) -> None:
    _remember_page_state(url, title, source="live_probe", verified=True)


def remember_search(query: str, search_url: str, results: list[dict[str, Any]] | None = None) -> None:
    _STATE["last_search_query"] = query
    _STATE["last_search_url"] = search_url
    _STATE["last_results"] = results or []
    _remember_page_state(search_url, f"Search: {query}", source="cache", verified=False)


def remember_page(title: str | None = None, url: str | None = None, *, source: str = "cache", verified: bool = False) -> None:
    _remember_page_state(url or _STATE.get("last_url"), title or _STATE.get("last_title"), source=source, verified=verified)


def invalidate_current_page(reason: str = "navigation changed") -> None:
    _STATE["verified"] = False
    _STATE["stale"] = True
    _STATE["source"] = "cache"
    _STATE["message"] = f"I can't verify the current Chrome page right now. Last known page may be stale after {reason}."


def current_state() -> dict[str, Any]:
    state = dict(_STATE)
    age = _age_seconds(str(state.get("captured_at") or state.get("updated_at") or ""))
    stale = True
    if age is not None:
        stale = bool(state.get("stale")) or age > CURRENT_PAGE_CACHE_TTL_SECONDS or not bool(state.get("verified"))
    state["age_seconds"] = age
    state["stale"] = stale
    state["url"] = state.get("url") or state.get("last_url")
    state["title"] = state.get("title") or state.get("last_title")
    state["captured_at"] = state.get("captured_at") or state.get("updated_at")
    if stale and state.get("url"):
        state["message"] = state.get("message") or f"I can't verify the current Chrome page right now. Last known page was {state.get('url')}."
    elif not state.get("url"):
        state["message"] = state.get("message") or "No browser page has been verified yet."
    return state


def make_observation(
    *,
    browser_detected: bool,
    active_window_title: str | None = None,
    current_url: str | None = None,
    current_title: str | None = None,
    source: str = "unknown",
    verified: bool = False,
    stale: bool = True,
    captured_at: str | None = None,
    age_seconds: float | None = None,
    message: str = "",
    tabs: list[dict[str, Any]] | None = None,
    page_summary: str | None = None,
    extracted_links: list[dict[str, str]] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    observation = BrowserObservation(
        timestamp=_now(),
        browser_detected=browser_detected,
        active_window_title=active_window_title,
        current_url=current_url,
        current_title=current_title,
        source=source,
        verified=verified,
        stale=stale,
        captured_at=captured_at,
        age_seconds=age_seconds,
        message=message,
        tabs=tabs or [],
        page_summary=page_summary,
        extracted_links=extracted_links or [],
        notes=notes or [],
    )
    return {"ok": True, **observation.as_dict()}
