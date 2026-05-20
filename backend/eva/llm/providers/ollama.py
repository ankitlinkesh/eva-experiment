from __future__ import annotations

from ...core.config import ModelSettings
from ...models.ollama import OllamaClient
from ..types import LLMResponse, Message


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings
        self.model = settings.fast_model or settings.ollama_model

    def available(self) -> bool:
        return True

    async def complete(self, messages: list[Message], temperature: float = 0.2, max_tokens: int = 800) -> LLMResponse:
        user = "\n".join(item.get("content", "") for item in messages if item.get("role") == "user").strip() or "Hello"
        history = [item for item in messages if item.get("role") in {"user", "assistant"}][:-1]
        try:
            text = await OllamaClient(self.settings).chat(user, history=history, model=self.model)
        except RuntimeError as exc:
            return LLMResponse(provider=self.name, model=self.model, ok=False, error=str(exc))
        return LLMResponse(provider=self.name, model=self.model, text=text, ok=bool(text), error=None if text else "empty_response")
