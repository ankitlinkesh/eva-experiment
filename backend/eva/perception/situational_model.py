"""A lightweight, opt-in situational model — perception & grounding (Phase 44).

Eva has been blind to what the user is actually doing. She can *ask* to read the
screen — the override-class ``screen.observe`` tool captures pixels behind the
permission gate — but that is a heavyweight, explicitly-authorized act, not
continuous awareness. So every plan has been ungrounded: Eva assumes the world
rather than looking at it.

This module gives Eva cheap, continuous *situational awareness* without the
privacy cost of screenshotting. The one rule:

  **Awareness is built from window/app METADATA, never from pixels.**

The OS already tells us, without reading any screen content, which application
is in the foreground and what windows are open (title + process name, via the
same window APIs the desktop tools use). That is enough to ground a plan —
"you're in VS Code", "Chrome is focused", "Slack and Spotify are also open" —
at a fraction of the sensitivity of a screenshot. Pixel capture stays exactly
where it was: the override-class ``screen.observe`` tool, governed by the gate.

Safety properties:

  * **No pixels, ever.** This module only reads window metadata. It never
    imports or triggers screen capture.
  * **Privacy redaction.** A foreground window whose title looks sensitive
    (banking, login, private messaging, ...) has its *title* suppressed to
    ``[private window]``; only the low-sensitivity process name survives. The
    open-apps list is process names only — never titles — so private page
    contents in a title bar can't leak through the situational model.
  * **Default-off, opt-in.** Gated behind ``EVA_PERCEPTION_ENABLED`` (default
    off, empty == off). No activation profile auto-enables it: awareness of what
    you're doing is a deliberate opt-in, one flag, by design. When off, every
    caller (including the agent-loop grounding hook) is a byte-identical no-op.
  * **Fail-safe.** Any error degrades to an "unavailable" situation, never an
    exception into the caller.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

_ABSENT = {"", "0", "false", "no", "off"}

# Window-title fragments that mark a foreground window as privacy-sensitive; its
# title is redacted out of the situational model. Kept in sync in spirit with
# screen_observer.PRIVATE_WINDOW_MARKERS, extended for the metadata setting.
_SENSITIVE_TITLE_MARKERS = (
    "whatsapp",
    "signal",
    "telegram",
    "messenger",
    "gmail",
    "outlook",
    "mail",
    "bank",
    "password",
    "signin",
    "sign in",
    "login",
    "log in",
    "account",
    "checkout",
    "payment",
    "wallet",
    "1password",
    "bitwarden",
    "keepass",
    "incognito",
    "private browsing",
)

_REDACTED_TITLE = "[private window]"
_MAX_TITLE_LEN = 80
_MAX_OPEN_APPS = 12


def perception_enabled(environ: dict[str, str] | None = None) -> bool:
    """Whether the situational model is active (default OFF, empty == off)."""
    env = environ if environ is not None else os.environ
    return env.get("EVA_PERCEPTION_ENABLED", "").strip().lower() not in _ABSENT


def _is_sensitive_title(title: str | None) -> bool:
    lowered = (title or "").lower()
    return any(marker in lowered for marker in _SENSITIVE_TITLE_MARKERS)


def _safe_title(title: str | None) -> str:
    """Redact a sensitive window title; otherwise trim to a safe length.

    Non-ASCII is preserved (traces/API are UTF-8) but callers that print to a
    legacy console should encode defensively — window titles carry arbitrary
    unicode.
    """
    if _is_sensitive_title(title):
        return _REDACTED_TITLE
    clean = " ".join(str(title or "").split())
    return clean[:_MAX_TITLE_LEN]


@dataclass(frozen=True)
class Situation:
    """A metadata-only snapshot of what the user is doing. No pixels involved."""

    active_app: str | None
    active_title: str | None
    open_apps: list[str] = field(default_factory=list)
    window_count: int = 0
    captured_at: str = ""
    privacy_redacted: bool = False
    available: bool = True
    source: str = "window_metadata"
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unavailable(detail: str) -> Situation:
    return Situation(
        active_app=None,
        active_title=None,
        open_apps=[],
        window_count=0,
        captured_at=datetime.now(timezone.utc).isoformat(),
        privacy_redacted=False,
        available=False,
        source="window_metadata",
        detail=detail,
    )


def capture_situation() -> Situation:
    """Snapshot the foreground app + open apps from window metadata only.

    Never captures pixels. Redacts sensitive foreground titles. Fail-safe: any
    error (or a non-Windows / headless host) yields an unavailable Situation.
    """
    try:
        from ..desktop.windows import get_active_window, list_open_windows

        active = get_active_window()
        windows = list_open_windows()
    except Exception as exc:  # pragma: no cover - platform/dependency guard
        return _unavailable(f"situational awareness unavailable: {str(exc)[:120]}")

    active_app = getattr(active, "process_name", None) or None
    raw_title = getattr(active, "title", None)
    redacted = _is_sensitive_title(raw_title)
    active_title = _safe_title(raw_title) if active_app else None

    # Open apps: distinct process names only (never titles), so a private page
    # in a title bar can't leak through the app list. Foreground app first.
    seen: list[str] = []
    for window in windows or []:
        name = getattr(window, "process_name", None)
        if name and name not in seen:
            seen.append(name)
    if active_app and active_app in seen:
        seen = [active_app] + [name for name in seen if name != active_app]
    open_apps = seen[:_MAX_OPEN_APPS]

    return Situation(
        active_app=active_app,
        active_title=active_title,
        open_apps=open_apps,
        window_count=len(windows or []),
        captured_at=datetime.now(timezone.utc).isoformat(),
        privacy_redacted=redacted,
        available=active_app is not None or bool(open_apps),
        source="window_metadata",
        detail="metadata-only situational snapshot (no screen capture)",
    )


def situational_summary(situation: Situation | None = None) -> str:
    """A compact grounding line describing the live situation.

    Empty string when perception is off or nothing is observable — callers treat
    "" as "add no grounding". Never raises.
    """
    try:
        # An explicitly-provided situation is always summarized (the caller
        # already holds it); only the auto-capture path honors the opt-in gate.
        if situation is None:
            if not perception_enabled():
                return ""
            situation = capture_situation()
        snap = situation
        if not snap.available:
            return ""
        parts: list[str] = []
        if snap.active_app:
            focus = snap.active_app
            # Re-apply redaction at the formatting boundary so a sensitive title
            # can never leak, however the Situation was constructed.
            safe_title = _safe_title(snap.active_title) if snap.active_title else ""
            if safe_title:
                focus += f" ({safe_title})"
            parts.append(f"Active app: {focus}")
        others = [app for app in snap.open_apps if app != snap.active_app]
        if others:
            parts.append("also open: " + ", ".join(others[:8]))
        if not parts:
            return ""
        return "Live situational context (from window metadata, no screenshot): " + "; ".join(parts) + "."
    except Exception:
        return ""


def ground_observation(situation: Situation | None = None) -> str:
    """The grounding string the agent loop injects, or "" to inject nothing.

    Thin alias over :func:`situational_summary` so the loop's intent reads
    clearly at the call site; both honor the default-off gate.
    """
    return situational_summary(situation)
