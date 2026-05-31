from __future__ import annotations

from typing import Any

from .base import EvaAgent


class BrowserAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="browser",
            description="Routes Chrome/web-app/page tasks to Browser Agent Core and Chrome Execution Skills.",
            capabilities=("browser", "chrome", "youtube", "chatgpt", "gmail", "github", "page", "url", "tab"),
            delegated_core="Browser Agent Core / Chrome Execution Skills",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(word in text for word in self.capabilities):
            return 0.93
        return 0.05
