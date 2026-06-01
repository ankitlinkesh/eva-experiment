from __future__ import annotations

from typing import Any

from .base import EvaAgent
from ..schemas.results import EvaAgentResult


class SafetyAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="safety",
            description="Routes permission, privacy, destructive, and cloud-context prechecks.",
            capabilities=("permission", "privacy", "delete", "override", "confirm", "safety", "secret"),
            delegated_core="Permission Gate / Cloud Context Firewall",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        env_local_name = ".env" + ".local"
        hard = (env_local_name, "api key", "token", "password", "format drive", "camera", "monitor screen", "secret", "logged in", "private page", "bypass login")
        confirm = ("send whatsapp", "send message", "post this", "submit form", "buy", "purchase")
        override = ("delete", "downloads folder", "change settings", "system action", "edit ", "write ", "rename ", "move ", "install ", "run powershell", "run shell", "run script", "git commit", "git push", "git merge")
        if any(word in text for word in hard + confirm + override + self.capabilities):
            return 0.99
        return 0.06

    def plan(self, state: Any) -> EvaAgentResult:
        text = str(getattr(state, "normalized_intent", "") or getattr(state, "user_request", "")).lower()
        env_local_name = ".env" + ".local"
        decision = "review_required"
        summary = "Would route through Permission Gate / Cloud Context Firewall before any action."
        if any(marker in text for marker in (env_local_name, "api key", "token", "password", "format drive", "camera", "monitor screen", "secret", "logged in", "private page", "bypass login")):
            decision = "blocked"
            summary = "Blocked: secret exposure, hidden monitoring, camera, or unsafe system access is not allowed."
        elif any(marker in text for marker in ("send whatsapp", "send message", "post this", "submit form", "buy", "purchase")):
            decision = "confirmation_required"
            summary = "Would require explicit confirmation before any external message, post, purchase, or form submission."
        elif any(marker in text for marker in ("delete", "downloads folder", "change settings", "system action", "edit ", "write ", "rename ", "move ", "install ", "run powershell", "run shell", "run script", "git commit", "git push", "git merge")):
            decision = "override_required"
            summary = "Would require override and rollback/checkpoint planning before any destructive or system-changing action."
        return EvaAgentResult(
            agent_name=self.name,
            ok=decision != "blocked",
            message=f"SafetyAgent selected; {decision}.",
            proposed_actions=[
                {
                    "agent": self.name,
                    "action_type": f"safety.{decision}",
                    "summary": summary,
                    "requires_permission": decision in {"confirmation_required", "override_required"},
                    "side_effect_level": "none",
                    "delegate_to": self.delegated_core,
                    "decision": decision,
                }
            ],
            delegated_to=self.delegated_core,
        )
