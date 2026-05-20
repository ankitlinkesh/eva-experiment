from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator

import httpx

from ..core.config import ModelSettings
from ..core.persona import EVA_SYSTEM_PROMPT


class GeminiClient:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is missing. Add it to eva-agent/.env.")

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        model: str | None = None,
    ) -> str:
        payload = self._payload(message, history)
        target_model = model or self.settings.smart_model
        url = self._url(target_model, stream=False)
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=5.0)) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:240]
            raise RuntimeError(f"Gemini request failed: HTTP {exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Gemini request failed: {exc}") from exc
        return self._extract_text(response.json())

    async def stream_chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        payload = self._payload(message, history)
        target_model = model or self.settings.smart_model
        url = self._url(target_model, stream=True)
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(None, connect=5.0)) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data_text = line.removeprefix("data:").strip()
                        if data_text == "[DONE]":
                            break
                        data = json.loads(data_text)
                        token = self._extract_text(data, allow_empty=True)
                        if token:
                            yield token
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:240]
            raise RuntimeError(f"Gemini stream failed: HTTP {exc.response.status_code}: {detail}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Gemini stream failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini stream returned invalid JSON.") from exc

    def _url(self, model: str, *, stream: bool) -> str:
        method = "streamGenerateContent?alt=sse" if stream else "generateContent"
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}"

    def _payload(self, message: str, history: list[dict[str, str]] | None) -> dict:
        contents = []
        for item in (history or [])[-6:]:
            role = "model" if item.get("role") == "assistant" else "user"
            text = str(item.get("content", "")).strip()
            if text:
                contents.append({"role": role, "parts": [{"text": text}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        return {
            "systemInstruction": {"parts": [{"text": EVA_SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.25,
                "maxOutputTokens": 512,
                "topP": 0.9,
            },
        }

    def _extract_text(self, data: dict, *, allow_empty: bool = False) -> str:
        parts: list[str] = []
        for candidate in data.get("candidates", []) or []:
            content = candidate.get("content", {}) or {}
            for part in content.get("parts", []) or []:
                text = part.get("text")
                if text:
                    parts.append(text)
        text = "".join(parts).strip()
        if not text and not allow_empty:
            raise RuntimeError("Gemini returned an empty response.")
        return text
