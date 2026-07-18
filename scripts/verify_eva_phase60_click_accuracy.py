"""Standalone verifier for Phase 60 (click accuracy) — bugs found by LIVE validation.

Phases 56-59 shipped a fully green suite that proved grounding produced the right
target. But installing uiautomation and driving a REAL click on a REAL Calculator
revealed two defects no fabricated-tree test could:

  1. DOUBLE-CENTERING: grounding emits a UiTarget whose (x,y) is the element's
     CENTER, but screen_controller.click_target added width/2 and height/2 again,
     so the click landed half a control away — it clicked the wrong button.
  2. DPI: UIAutomation reports physical pixels; a non-DPI-aware process makes
     pyautogui act in scaled pixels, so on any display scaled != 100% every click
     misses. The process must be made DPI-aware, and the coordinate READER
     (grounding) and the coordinate ACTOR (pyautogui) must share that context.

The live proof: after the fix, screen.click(label="Seven") on Calculator moved
the real display from "77" to "777" — it located a button by name and clicked it.
This verifier locks in the invariants so they cannot silently regress.

Fully offline: no real desktop needed to check the invariants themselves.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.agent.action_model import AgentObservation
    from backend.eva.screen import dpi, screen_controller as sc
    from backend.eva.screen.ui_locator import UiTarget
    from scripts import verify_eva_all

    # 1. click_target clicks the CENTER POINT grounding gave — not re-centered.
    seen = {}

    original_click = sc.click
    try:
        sc.click = lambda x, y, reason, action_id="screen.click": (
            seen.__setitem__("xy", (x, y)) or AgentObservation(action_id, True, {}, "ok")
        )
        target = UiTarget.from_dict(
            {"label": "Seven", "role": "button", "x": 133, "y": 482, "width": 258, "height": 79, "confidence": 1.0, "method": "uiautomation"}
        )
        sc.click_target(target, "verify")
        check(seen.get("xy") == (133, 482), f"click must use the center point (133,482), not an offset, got {seen.get('xy')}")

        # A low-confidence target must never reach the click.
        seen.clear()
        weak = UiTarget.from_dict({"label": "x", "x": 1, "y": 2, "width": 4, "height": 4, "confidence": 0.5, "method": "uiautomation"})
        obs = sc.click_target(weak, "verify")
        check(obs.success is False and "xy" not in seen, "a low-confidence target must not be clicked")
    finally:
        sc.click = original_click

    # 2. DPI awareness is idempotent and safe, and both the read + click paths use it.
    check(dpi.ensure_dpi_aware() is dpi.ensure_dpi_aware(), "ensure_dpi_aware must be idempotent")

    controller_src = (ROOT / "backend" / "eva" / "screen" / "screen_controller.py").read_text(encoding="utf-8")
    grounding_src = (ROOT / "backend" / "eva" / "screen" / "grounding.py").read_text(encoding="utf-8")
    check("ensure_dpi_aware" in controller_src, "the click path must ensure DPI awareness")
    check("ensure_dpi_aware" in grounding_src, "the grounding read path must ensure DPI awareness")
    check("click_x = int(target.x)" in controller_src, "click_target must click the target's center point directly")
    check("target.width / 2" not in controller_src, "click_target must not add width/2 back to an already-centered point")

    # 3. Registration.
    name = "verify_eva_phase60_click_accuracy.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 60 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 60 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 60 verifier")

    print(
        "PASS: Phase 60 click accuracy -- two bugs a fully green suite missed, found only by driving a REAL click. "
        "click_target now clicks the exact center point grounding emits (it used to add width/2 and land half a "
        "control away), and the process is made DPI-aware so the coordinate reader (grounding) and actor (pyautogui) "
        "share one pixel space (a non-DPI-aware process misses every click on a scaled display). Live proof: "
        "screen.click(label='Seven') moved Calculator's display from 77 to 777."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
