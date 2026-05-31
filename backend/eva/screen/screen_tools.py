from __future__ import annotations

from typing import Any

from ..agent.action_model import AgentAction
from ..security.action_types import ActionType
from ..security.permission_gate import PermissionContext, evaluate_action
from . import screen_controller
from .screen_observer import observe_screen_once
from .ui_locator import UiTarget


def _decision(tool_name: str, action_type: ActionType, reason: str, **params: Any) -> dict[str, Any] | None:
    action = AgentAction(tool_name=tool_name, action_type=action_type.value, description=reason, params=params, risk_categories=[action_type.value], privacy_sensitive=action_type == ActionType.PRIVACY_SCREEN_READ)
    decision = evaluate_action(action, PermissionContext())
    if decision.decision != "allow":
        return {"ok": False, "requires_permission": True, "decision": decision.as_dict()}
    return None


def screen_observe(reason: str) -> dict[str, Any]:
    if not str(reason or "").strip():
        return {"ok": False, "error": "reason_required", "message": "Screen observation requires an active task reason."}
    denied = _decision("screen.observe", ActionType.PRIVACY_SCREEN_READ, reason)
    if denied:
        return denied
    observation = observe_screen_once(reason)
    return {**observation.as_dict(), "ui_events": [{"type": "observing_screen", "reason": reason}]}


def screen_click(
    x: int | None = None,
    y: int | None = None,
    reason: str = "",
    target: dict[str, Any] | None = None,
    required_confidence: float = 0.75,
) -> dict[str, Any]:
    if not str(reason or "").strip():
        return {"ok": False, "error": "reason_required", "message": "Screen click requires an active task reason."}
    if target is None:
        return {
            "ok": False,
            "error": "ui_target_required",
            "message": "I will not click raw coordinates. I need a verified UI target with confidence and a reason.",
            "ui_events": [{"type": "ui_target_low_confidence", "reason": "missing_target"}],
        }
    ui_target = UiTarget.from_dict(target)
    if ui_target.confidence < float(required_confidence):
        return {
            "ok": False,
            "error": "ui_target_low_confidence",
            "target": ui_target.as_dict(),
            "message": f"I found {ui_target.label}, but confidence was too low to click safely.",
            "ui_events": [{"type": "ui_target_low_confidence", "target": ui_target.as_dict()}],
        }
    denied = _decision("screen.click", ActionType.SAFE_LOCAL_UI, reason, target=ui_target.as_dict())
    if denied:
        return denied
    obs = screen_controller.click_target(ui_target, reason)
    return {
        "ok": obs.success,
        **obs.as_dict(),
        "ui_events": [
            {"type": "ui_target_found", "target": ui_target.as_dict()},
            {"type": "executing_visible_action", "action": "click", "reason": reason},
        ],
    }


def screen_type_text(text: str, reason: str) -> dict[str, Any]:
    if not str(reason or "").strip():
        return {"ok": False, "error": "reason_required", "message": "Typing requires an active task reason."}
    denied = _decision("screen.type_text", ActionType.SAFE_LOCAL_UI, reason)
    if denied:
        return denied
    obs = screen_controller.type_text_visible(text, reason)
    return {"ok": obs.success, **obs.as_dict()}


def screen_hotkey(keys: list[str], reason: str) -> dict[str, Any]:
    if not str(reason or "").strip():
        return {"ok": False, "error": "reason_required", "message": "Hotkey requires an active task reason."}
    denied = _decision("screen.hotkey", ActionType.SAFE_LOCAL_UI, reason)
    if denied:
        return denied
    obs = screen_controller.hotkey_bounded(keys, reason)
    return {"ok": obs.success, **obs.as_dict()}


def screen_press(key: str, reason: str) -> dict[str, Any]:
    if not str(reason or "").strip():
        return {"ok": False, "error": "reason_required", "message": "Key press requires an active task reason."}
    denied = _decision("screen.press", ActionType.SAFE_LOCAL_UI, reason)
    if denied:
        return denied
    obs = screen_controller.press_key_bounded(key, reason)
    return {"ok": obs.success, **obs.as_dict()}


def screen_scroll(amount: int, reason: str) -> dict[str, Any]:
    if not str(reason or "").strip():
        return {"ok": False, "error": "reason_required", "message": "Scroll requires an active task reason."}
    denied = _decision("screen.scroll", ActionType.SAFE_LOCAL_UI, reason)
    if denied:
        return denied
    obs = screen_controller.scroll(amount, reason)
    return {"ok": obs.success, **obs.as_dict()}


def screen_wait(seconds: float, reason: str) -> dict[str, Any]:
    obs = screen_controller.wait(seconds, reason)
    return {"ok": obs.success, **obs.as_dict()}
