from __future__ import annotations

from typing import Any

from .base import EvaAgent
from ..schemas.results import EvaAgentResult


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
        if any(word in text for word in ("browser", "chrome", "page", "url", "tab", "chatgpt", "gmail", "github", "open site", "copy current url", "what page")):
            return 0.93
        return 0.05

    def plan(self, state: Any) -> EvaAgentResult:
        text = str(getattr(state, "normalized_intent", "") or getattr(state, "user_request", "")).lower()
        site = "ChatGPT" if "chatgpt" in text else "GitHub" if "github" in text else "Chrome"
        action_type = "browser.delegate_existing_chrome_skill"
        summary = f"Would delegate to existing Chrome Execution Skills to open or inspect {site}."
        if "copy current url" in text:
            action_type = "browser.copy_current_url"
            summary = "Would use Browser Agent Core to live-probe and copy the current verified URL."
        elif "what page" in text:
            action_type = "browser.current_page"
            summary = "Would use Browser Agent Core to verify the current Chrome page."
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message="BrowserAgent selected for a browser or Chrome preview.",
            proposed_actions=[
                {
                    "agent": self.name,
                    "action_type": action_type,
                    "summary": summary,
                    "requires_permission": False,
                    "side_effect_level": "low",
                    "delegate_to": self.delegated_core,
                }
            ],
            delegated_to=self.delegated_core,
        )
