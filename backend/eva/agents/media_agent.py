from __future__ import annotations

from typing import Any

from .base import EvaAgent
from ..schemas.results import EvaAgentResult


class MediaAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="media",
            description="Routes Spotify/YouTube music controls to existing media and browser skills.",
            capabilities=("spotify", "music", "song", "play", "pause", "youtube", "track", "media"),
            delegated_core="Spotify Desktop Skill / YouTube Chrome Skill",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(word in text for word in ("spotify", "song", "music", "track", "pause", "next song", "previous song", "play ")):
            return 0.92
        if "youtube" in text and "play" in text:
            return 0.92
        return 0.03

    def plan(self, state: Any) -> EvaAgentResult:
        text = str(getattr(state, "normalized_intent", "") or getattr(state, "user_request", "")).lower()
        target = "YouTube Chrome skill" if "youtube" in text else "Spotify Desktop Skill"
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message=f"MediaAgent selected for a media preview using {target}.",
            proposed_actions=[
                {
                    "agent": self.name,
                    "action_type": "media.delegate_spotify_or_youtube",
                    "summary": f"Would delegate to {target} depending on the requested source and target.",
                    "requires_permission": False,
                    "side_effect_level": "low",
                    "delegate_to": self.delegated_core,
                }
            ],
            delegated_to=self.delegated_core,
        )
