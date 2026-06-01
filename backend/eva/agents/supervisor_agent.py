from __future__ import annotations

from typing import Any
from dataclasses import asdict, dataclass

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


@dataclass
class AgentSelection:
    agent: EvaAgent
    score: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["agent"] = self.agent.as_dict()
        return data


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
    return select_agent_with_reason(intent, state).agent


def select_agent_with_reason(intent: str, state: Any | None = None) -> AgentSelection:
    text = str(intent or "").lower()
    agents = build_default_agents()
    scored = [(agent.can_handle(text, state), agent) for agent in agents]
    if _looks_code_readonly_request(text) and not _looks_safety_sensitive(text):
        code = next(agent for agent in agents if agent.name == "code")
        return AgentSelection(code, max(0.93, code.can_handle(text, state)), "Read-only code index request should preview Code Intelligence.")
    if _looks_safety_sensitive(text):
        safety = next(agent for agent in agents if agent.name == "safety")
        return AgentSelection(safety, max(0.99, safety.can_handle(text, state)), "Safety-sensitive, destructive, secret, or external-visible request.")
    if _looks_media_request(text):
        media = next(agent for agent in agents if agent.name == "media")
        return AgentSelection(media, max(0.92, media.can_handle(text, state)), "Media/music intent should preview Spotify or YouTube media skills.")
    if _looks_memory_request(text):
        memory = next(agent for agent in agents if agent.name == "memory")
        return AgentSelection(memory, max(0.88, memory.can_handle(text, state)), "Memory intent should preview local SQLite memory handling.")
    if _looks_browser_request(text):
        browser = next(agent for agent in agents if agent.name == "browser")
        return AgentSelection(browser, max(0.93, browser.can_handle(text, state)), "Browser or web-app intent should preview Browser Agent Core / Chrome skills.")
    best_score, best_agent = sorted(scored, key=lambda item: item[0], reverse=True)[0]
    return AgentSelection(best_agent, best_score, f"Highest capability score for {best_agent.name}.")


def _looks_safety_sensitive(text: str) -> bool:
    env_local_name = ".env" + ".local"
    return any(
        marker in text
        for marker in (
            env_local_name,
            "api key",
            "token",
            "password",
            "format drive",
            "delete",
            "edit ",
            "write ",
            "rename ",
            "move ",
            "install ",
            "pip " + "install",
            "run powershell",
            "run shell",
            "run script",
            "git commit",
            "git push",
            "git merge",
            "logged in",
            "private page",
            "bypass login",
            "send whatsapp",
            "send message",
            "post this",
            "submit form",
            "buy",
            "purchase",
            "monitor screen",
            "turn on camera",
            "camera",
            "secret",
        )
    )


def _looks_media_request(text: str) -> bool:
    return any(marker in text for marker in ("spotify", "song", "music", "next song", "previous song", "pause music")) or (
        "play " in text and not _looks_browser_request(text)
    ) or ("youtube" in text and "play" in text)


def _looks_browser_request(text: str) -> bool:
    return any(marker in text for marker in ("open ", "chrome", "browser", "page", "url", "github", "chatgpt", "gmail", "what page", "copy current url", "search youtube")) and not any(
        marker in text for marker in ("logged in", "private page", "bypass login")
    )


def _looks_memory_request(text: str) -> bool:
    return any(marker in text for marker in ("remember that", "remember this", "recall", "what do you remember", "save this memory", "memory"))


def _looks_code_readonly_request(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "code index",
            "code status",
            "search code",
            "code search",
            "symbol search",
            "code symbols",
            "find symbol",
            "where is symbol",
            "workspace summary",
            "summarize workspace",
            "summarise workspace",
            "summarize backend/",
            "summarise backend/",
        )
    )
