from __future__ import annotations

from typing import Any

from .base import EvaAgent
from .browser_agent import BrowserAgent
from .code_agent import CodeAgent
from .desktop_agent import DesktopAgent
from .media_agent import MediaAgent
from .memory_agent import MemoryAgent
from .research_agent import ResearchAgent
from .safety_agent import SafetyAgent


class SupervisorAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="supervisor",
            description="Selects a specialist v2 skeleton agent and delegates execution to existing Eva systems.",
            capabilities=("route", "classify", "delegate", "supervise"),
            delegated_core="Capability Router / existing Eva agent loop",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        return 0.2


def build_default_agents() -> list[EvaAgent]:
    return [
        SupervisorAgent(),
        BrowserAgent(),
        DesktopAgent(),
        MediaAgent(),
        CodeAgent(),
        ResearchAgent(),
        SafetyAgent(),
        MemoryAgent(),
    ]


def select_agent_for_intent(intent: str, state: Any | None = None) -> EvaAgent:
    agents = build_default_agents()
    scored = [(agent.can_handle(intent, state), agent) for agent in agents]
    return sorted(scored, key=lambda item: item[0], reverse=True)[0][1]
