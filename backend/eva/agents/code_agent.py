from __future__ import annotations

from typing import Any

from .base import EvaAgent


class CodeAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="code",
            description="Routes implementation-location, symbol, traceback, and patch-plan tasks to Code Intelligence.",
            capabilities=("code", "symbol", "traceback", "implemented", "where is", "patch", "debug"),
            delegated_core="Code Intelligence v1",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(word in text for word in ("code", "symbol", "traceback", "implemented", "where is", "debug", "patch")):
            return 0.9
        return 0.04
