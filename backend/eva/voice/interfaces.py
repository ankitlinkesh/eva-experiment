from __future__ import annotations

from typing import Protocol


class SpeechToText(Protocol):
    async def transcribe(self, audio: bytes) -> str:
        """Convert audio bytes to text."""


class TextToSpeech(Protocol):
    async def synthesize(self, text: str) -> bytes:
        """Convert text to playable audio bytes."""


class WakeWordDetector(Protocol):
    async def detect(self, audio: bytes) -> bool:
        """Return true when Eva should wake up."""
