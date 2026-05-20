from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from ..core.config import ModelSettings
from ..core.persona import EVA_SYSTEM_PROMPT


class OllamaClient:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        model: str | None = None,
    ) -> str:
        payload = self._payload(message, history, stream=False, model=model)

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=3.0)) as client:
                response = await client.post(f"{self.settings.ollama_url}/api/chat", json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama returned invalid JSON: {response.text[:180]}") from exc

        content = data.get("message", {}).get("content", "")
        return content.strip() or "I heard you, but the local model returned an empty response."

    async def stream_chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        payload = self._payload(message, history, stream=True, model=model)

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=3.0)) as client:
                async with client.stream("POST", f"{self.settings.ollama_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama stream failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama stream returned invalid JSON.") from exc

    def _payload(
        self,
        message: str,
        history: list[dict[str, str]] | None,
        *,
        stream: bool,
        model: str | None,
    ) -> dict:
        history = history or []
        messages = [{"role": "system", "content": EVA_SYSTEM_PROMPT}]
        messages.extend({"role": item["role"], "content": item["content"]} for item in history[-4:])
        messages.append({"role": "user", "content": message})
        return {
            "model": model or self.settings.ollama_model,
            "messages": messages,
            "stream": stream,
            "keep_alive": "10m",
            "options": {
                "temperature": 0.15,
                "num_ctx": 2048,
                "num_predict": 120,
            },
        }
