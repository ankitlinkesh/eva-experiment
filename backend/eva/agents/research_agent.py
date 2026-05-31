from __future__ import annotations

from typing import Any

from .base import EvaAgent


class ResearchAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="research",
            description="Routes saved research, Tavily-backed web research, and local research summaries.",
            capabilities=("research", "tavily", "sources", "knowledge", "what do we know"),
            delegated_core="Research SQLite / Tavily",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(word in text for word in ("research", "sources", "knowledge", "what do we know", "tavily")):
            return 0.87
        return 0.04
