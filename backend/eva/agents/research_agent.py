from __future__ import annotations

from typing import Any

from .base import EvaAgent
from ..schemas.results import EvaAgentResult


class ResearchAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="research",
            description="Routes saved research, Tavily-backed public research, and local Research Memory v2 summaries.",
            capabilities=("research", "research memory", "tavily", "sources", "knowledge", "what do we know"),
            delegated_core="Research SQLite / Research Memory v2 / Tavily",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(word in text for word in ("research", "research memory", "sources", "knowledge", "what do we know", "tavily", "search latest", "latest", "news", "look up", "find sources", "summarize webpage", "public search")):
            return 0.87
        return 0.04

    def plan(self, state: Any) -> EvaAgentResult:
        text = str(getattr(state, "normalized_intent", "") or getattr(state, "user_request", "")).lower()
        relevant_memory = getattr(state, "relevant_memory", []) or []
        action_type = "research.public_search"
        summary = "Would search or summarize public research through existing safe research helpers."
        if any(marker in text for marker in ("gmail", "email", "chat", "logged in", "private page", "scrape", "bypass", "paywall", "hidden credential", "cookies")):
            action_type = "research.private_account_read"
            summary = "Would require private/logged-in content access, which v2 read-only execution must refuse."
        elif "dump all" in text and "research memory" in text:
            action_type = "research.memory_search"
            summary = "Full dump refused. Would redirect to `research memory search <query>`, `research memory export`, or `research memory topics`."
        elif text in {"research memory retrieval status", "research memory vector status"}:
            action_type = "research.status"
            summary = "Would read local Research Memory retrieval/vector status."
        elif text in {"research memory status", "research status", "research knowledge status"} or "research status" in text:
            action_type = "research.status"
            summary = "Would read local research status."
        elif relevant_memory:
            action_type = "research.memory_search"
            summary = "Would answer using local Research Memory v2 hybrid retrieval. No live web search was executed."
        elif text.startswith("search research memory ") or text.startswith("research memory search ") or text.startswith("research memory retrieve "):
            action_type = "research.memory_search"
            summary = "Would search local Research Memory v2 through local hybrid retrieval planning."
        elif text.startswith("summarize research topic ") or text.startswith("summarise research topic ") or text.startswith("research topic "):
            action_type = "research.memory_topic_summary"
            summary = "Would summarize a local Research Memory v2 topic."
        elif text.startswith("save research note ") or text.startswith("remember research "):
            action_type = "research.memory_save"
            summary = "Would save a user-approved research note to local Research Memory v2."
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
                    "delegate_to": "Research Memory v2 hybrid retrieval planner / Research SQLite / Tavily",
                }
            ],
            delegated_to="Research Memory v2 hybrid retrieval planner / Research SQLite / Tavily",
        )
