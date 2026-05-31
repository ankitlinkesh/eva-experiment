from __future__ import annotations

from typing import Any

from ..agent.action_model import AgentAction
from ..security.action_types import ActionType
from ..security.permission_gate import PermissionContext, evaluate_action


_DRAFTS: dict[str, dict[str, str]] = {}


def message_prepare(recipient: str, message: str) -> dict[str, Any]:
    key = recipient.strip().lower() or "current"
    _DRAFTS[key] = {"recipient": recipient, "message": message}
    return {"ok": True, "recipient": recipient, "message": message, "draft_prepared": True, "verification": {"verified": True, "confidence": 0.8}}


def message_confirm_send(recipient: str, message: str) -> dict[str, Any]:
    return {"ok": False, "requires_confirmation": True, "message": f"Send this message to {recipient}: {message}"}


def message_send_via_ui(recipient: str, message: str, confirmed: bool = False) -> dict[str, Any]:
    action = AgentAction(
        "message.send_via_ui",
        ActionType.EXTERNAL_MESSAGE_SEND.value,
        "Send visible external message",
        {"recipient": recipient, "message": message},
        [ActionType.EXTERNAL_MESSAGE_SEND.value],
        external_visible=True,
        verification={"method": "message_sent_likely"},
    )
    decision = evaluate_action(action, PermissionContext(user_confirmed=bool(confirmed)))
    if decision.decision != "allow":
        return {"ok": False, "requires_confirmation": True, "decision": decision.as_dict(), "message": f"Confirm before sending this message to {recipient}: {message}"}
    return {"ok": True, "recipient": recipient, "sent_likely": True, "message": "Message send action completed through visible UI. I could not fully verify delivery."}
