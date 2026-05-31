from __future__ import annotations

from typing import Any

from .base import EvaAgent


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
        if any(word in text for word in self.capabilities):
            return 0.94
        return 0.06
