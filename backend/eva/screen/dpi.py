"""Process DPI awareness — so on-screen coordinates actually line up (Phase 60).

Discovered by live validation: UIAutomation reports element rectangles in
PHYSICAL pixels, but a process that is not DPI-aware makes pyautogui move/click
in SCALED logical pixels. On any display with scaling other than 100% the two
disagree and every click lands in the wrong place. Making the process DPI-aware
puts the coordinate reader (grounding) and the coordinate actor (pyautogui) in
the same space.

Idempotent and fail-safe: it can only be set once per process, so both the
grounding read path and the click path call this and whichever runs first wins;
a failure (already set via manifest, or an old OS) is swallowed.
"""

from __future__ import annotations

_ensured = False


def ensure_dpi_aware() -> bool:
    """Make this process per-monitor DPI-aware (best effort, once). Idempotent."""
    global _ensured
    if _ensured:
        return True
    _ensured = True  # attempt at most once; process DPI state is set for good
    try:
        import ctypes

        try:
            # PROCESS_PER_MONITOR_DPI_AWARE = 2 (Win 8.1+)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return True
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()  # older fallback
            return True
    except Exception:
        return False


__all__ = ["ensure_dpi_aware"]
