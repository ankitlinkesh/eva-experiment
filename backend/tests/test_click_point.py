"""Click-point + DPI correctness (Phase 60) — bugs found by live validation.

A green test suite proved grounding produced the right target; only driving a
real click on a real screen revealed that the click landed half a control away
(click_target re-centered an already-centered point) and that coordinates only
line up when the process is DPI-aware.
"""

from __future__ import annotations

from eva.agent.action_model import AgentObservation
from eva.screen import dpi, screen_controller as sc
from eva.screen.ui_locator import UiTarget


def _target():
    # Exactly what grounding emits for Calculator's "Seven": x,y is the CENTER.
    return UiTarget.from_dict(
        {"label": "Seven", "role": "button", "x": 133, "y": 482, "width": 258, "height": 79, "confidence": 1.0, "method": "uiautomation"}
    )


def test_click_target_clicks_the_center_point_not_offset(monkeypatch):
    seen = {}

    def fake_click(x, y, reason, action_id="screen.click"):
        seen["xy"] = (x, y)
        return AgentObservation(action_id=action_id, success=True, raw_observation={}, summary="ok")

    monkeypatch.setattr(sc, "click", fake_click)
    sc.click_target(_target(), "test click")
    # The point grounding gave — NOT (133 + 258/2, 482 + 79/2) = (262, 521).
    assert seen["xy"] == (133, 482)


def test_low_confidence_target_is_not_clicked(monkeypatch):
    clicked = {"n": 0}
    monkeypatch.setattr(sc, "click", lambda *a, **k: clicked.__setitem__("n", clicked["n"] + 1) or AgentObservation("x", True, {}, "ok"))
    weak = UiTarget.from_dict({"label": "Seven", "x": 133, "y": 482, "width": 10, "height": 10, "confidence": 0.5, "method": "uiautomation"})
    obs = sc.click_target(weak, "test")
    assert obs.success is False
    assert clicked["n"] == 0  # never reached the click


def test_ensure_dpi_aware_is_idempotent_and_safe():
    # Whatever the platform, it must return a bool and never raise on repeat calls.
    first = dpi.ensure_dpi_aware()
    second = dpi.ensure_dpi_aware()
    assert isinstance(first, bool) and second is True
