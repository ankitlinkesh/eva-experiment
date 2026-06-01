from __future__ import annotations

from typing import Any

from .base import EvaAgent
from ..schemas.results import EvaAgentResult


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
        if any(word in text for word in ("research", "sources", "knowledge", "what do we know", "tavily", "search latest", "latest", "news", "look up", "find sources", "summarize webpage", "public search")):
            return 0.87
        return 0.04

    def plan(self, state: Any) -> EvaAgentResult:
        text = str(getattr(state, "normalized_intent", "") or getattr(state, "user_request", "")).lower()
        action_type = "research.public_search"
        summary = "Would search or summarize public research through existing safe research helpers."
        if text in {"research status", "research knowledge status"} or "research status" in text:
            action_type = "research.status"
            summary = "Would read local research status."
        elif any(marker in text for marker in ("logged in", "private page", "gmail", "email", "chat", "bypass", "paywall", "hidden credential")):
            action_type = "research.private_account_read"
            summary = "Would require private/logged-in content access, which v2 read-only execution must refuse."
        elif text.startswith("research ") and len(text.split()) > 1:
            action_type = "research.safe_lookup"
            summary = "Would look up saved local research or use safe public research if configured."
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message="ResearchAgent selected for a research preview.",
            proposed_actions=[
                {
                    "agent": self.name,
                    "action_type": action_type,
                    "summary": summary,
                    "requires_permission": False,
                    "side_effect_level": "read_only",
                    "delegate_to": self.delegated_core,
                }
            ],
            delegated_to=self.delegated_core,
        )
