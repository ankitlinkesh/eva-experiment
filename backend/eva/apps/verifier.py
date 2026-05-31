from __future__ import annotations

from typing import Any

from .playbooks import get_playbook


def verification_rules_for(app_name: str) -> dict[str, Any]:
    playbook = get_playbook(app_name)
    if playbook is None:
        return {"ok": False, "error": "playbook_not_found", "app": app_name}
    return {
        "ok": True,
        "app": playbook.app_name,
        "verification_rules": list(playbook.verification_rules),
        "repair_rules": list(playbook.repair_rules),
        "blocked_contexts": list(playbook.blocked_contexts),
    }
