from __future__ import annotations

from typing import Any

from .playbooks import get_playbook


def describe_app_automation(app_name: str) -> dict[str, Any]:
    playbook = get_playbook(app_name)
    if playbook is None:
        return {"ok": False, "error": "playbook_not_found", "app": app_name}
    return {
        "ok": True,
        "app": playbook.app_name,
        "allowed_actions": list(playbook.allowed_actions),
        "allowed_hotkeys": list(playbook.allowed_hotkeys),
        "allowed_text_input": playbook.allowed_text_input,
        "ui_target_hints": playbook.ui_target_hints,
    }
