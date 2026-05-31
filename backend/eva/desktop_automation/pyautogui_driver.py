from __future__ import annotations

from typing import Any

from ..runtime.feature_flags import get_v2_feature_flags
from .ui_targets import UiTarget


def is_pyautogui_available() -> bool:
    try:
        import pyautogui  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def pyautogui_status() -> dict[str, Any]:
    flags = get_v2_feature_flags()
    available = is_pyautogui_available()
    enabled = bool(flags.pyautogui_enabled and available)
    return {
        "ok": True,
        "available": available,
        "enabled": enabled,
        "message": "PyAutoGUI strict adapter is optional and disabled unless EVA_V2_PYAUTOGUI_ENABLED=true.",
        "safety": "Requires active task id, reason, and high-confidence UiTarget for clicks.",
    }


def _validate_task(reason: str, task_id: str | None) -> dict[str, Any] | None:
    if not str(reason or "").strip():
        return {"ok": False, "error": "reason_required"}
    if not str(task_id or "").strip():
        return {"ok": False, "error": "active_task_required"}
    return None


def click_target(ui_target: Any, reason: str, task_id: str | None, required_confidence: float = 0.75) -> dict[str, Any]:
    invalid = _validate_task(reason, task_id)
    if invalid:
        return invalid
    target = UiTarget.from_value(ui_target)
    if target is None:
        return {"ok": False, "error": "UiTarget object with confidence is required; raw coordinates are refused."}
    if target.confidence < required_confidence:
        return {"ok": False, "error": f"UiTarget confidence {target.confidence:.2f} is below required {required_confidence:.2f}.", "target": target.as_dict()}
    status = pyautogui_status()
    if not status["enabled"]:
        return {"ok": False, "error": "pyautogui_disabled", "target": target.as_dict(), "message": status["message"]}
    return {"ok": False, "error": "phase1_no_direct_click", "target": target.as_dict()}


def type_text(text: str, reason: str, task_id: str | None) -> dict[str, Any]:
    invalid = _validate_task(reason, task_id)
    if invalid:
        return invalid
    if not pyautogui_status()["enabled"]:
        return {"ok": False, "error": "pyautogui_disabled"}
    return {"ok": False, "error": "phase1_no_direct_type", "chars": len(text)}


def press_key(key: str, reason: str, task_id: str | None) -> dict[str, Any]:
    invalid = _validate_task(reason, task_id)
    if invalid:
        return invalid
    if not pyautogui_status()["enabled"]:
        return {"ok": False, "error": "pyautogui_disabled"}
    return {"ok": False, "error": "phase1_no_direct_key", "key": key}


def hotkey(keys: list[str], reason: str, task_id: str | None) -> dict[str, Any]:
    invalid = _validate_task(reason, task_id)
    if invalid:
        return invalid
    if not pyautogui_status()["enabled"]:
        return {"ok": False, "error": "pyautogui_disabled"}
    return {"ok": False, "error": "phase1_no_direct_hotkey", "keys": keys}


def observe_after_action(reason: str, task_id: str | None) -> dict[str, Any]:
    invalid = _validate_task(reason, task_id)
    if invalid:
        return invalid
    return {"ok": True, "source": "existing_screen_observer", "message": "Use existing one-shot screen observer for Phase 1."}


def verify_desktop_state(expected: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "verified": False, "confidence": 0.35, "expected": expected, "message": "Desktop verification interface is ready; existing verifier remains primary."}
