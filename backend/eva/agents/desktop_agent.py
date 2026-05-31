from __future__ import annotations

from typing import Any

from .base import EvaAgent


class DesktopAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="desktop",
            description="Routes visible desktop/window tasks to Desktop Agent Core and Visual Desktop Control.",
            capabilities=("desktop", "window", "screen", "click", "type", "focus", "notepad", "vscode", "file explorer"),
            delegated_core="Desktop Agent Core / Visual Desktop Control",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(word in text for word in self.capabilities):
            return 0.86
        return 0.04
