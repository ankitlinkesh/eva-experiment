from __future__ import annotations

from typing import Any

from .base import EvaAgent


class MemoryAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="memory",
            description="Routes local memory facts, task context, and future vector-memory retrieval.",
            capabilities=("memory", "remember", "recall", "task context", "preference"),
            delegated_core="Memory SQLite / TaskContext / vector memory interface",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(word in text for word in ("memory", "remember", "recall", "preference")):
            return 0.88
        return 0.04
