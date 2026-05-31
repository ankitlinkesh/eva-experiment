from __future__ import annotations

from typing import Any

from .base import EvaAgent


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
        if any(word in text for word in ("spotify", "song", "music", "track", "pause", "play ")):
            return 0.92
        if "youtube" in text and "play" in text:
            return 0.88
        return 0.03
