from __future__ import annotations

from typing import Any

from .base import EvaAgent
from ..schemas.results import EvaAgentResult


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
        if any(word in text for word in ("memory", "remember", "recall", "preference", "what do you remember", "save this memory")):
            return 0.88
        return 0.04

    def plan(self, state: Any) -> EvaAgentResult:
        text = str(getattr(state, "normalized_intent", "") or getattr(state, "user_request", "")).lower()
        if "delete" in text or "forget" in text:
            action_type = "memory.delete"
            side_effect = "destructive"
            summary = "Would delete local memory, which v2 read-only execution must refuse."
        elif "dump" in text or "database" in text or "raw" in text:
            action_type = "memory.dump_database"
            side_effect = "privacy_sensitive"
            summary = "Would expose raw memory data, which v2 read-only execution must refuse."
        elif text.startswith("recall") or "what you remember" in text or "what do you remember" in text:
            action_type = "memory.recall"
            side_effect = "read_only"
            summary = "Would recall approved local memory facts as a summary."
        elif "remember" in text or "save this memory" in text:
            action_type = "memory.write"
            side_effect = "local_write"
            summary = "Would write local memory through the existing memory handler."
        elif "status" in text:
            action_type = "memory.status"
            side_effect = "read_only"
            summary = "Would read local memory status."
        else:
            action_type = "memory.recall"
            side_effect = "read_only"
            summary = "Would recall approved local memory facts as a summary."
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message="MemoryAgent selected for a local memory preview.",
            proposed_actions=[
                {
                    "agent": self.name,
                    "action_type": action_type,
                    "summary": summary,
                    "requires_permission": False,
                    "side_effect_level": side_effect,
                    "delegate_to": self.delegated_core,
                }
            ],
            delegated_to=self.delegated_core,
        )
