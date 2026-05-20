from __future__ import annotations

import os

import httpx

from ...core.config import ModelSettings
from ..types import LLMResponse, Message, headers_to_dict, retry_after_from_headers


class GeminiProvider:
    name = "gemini"

    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings
        self.api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self.model = os.environ.get("GEMINI_MODEL", settings.smart_model or "gemini-2.5-flash").strip() or "gemini-2.5-flash"

    def available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, messages: list[Message], temperature: float = 0.2, max_tokens: int = 800) -> LLMResponse:
        if not self.available():
            return LLMResponse(provider=self.name, model=self.model, ok=False, error="missing_api_key")
        system_text, contents = self._gemini_contents(messages)
        payload = {
            "systemInstruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens, "topP": 0.9},
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=5.0)) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            return LLMResponse(provider=self.name, model=self.model, ok=False, error=str(exc))
        raw_headers = headers_to_dict(response.headers)
        if response.status_code >= 400:
            retry_after = retry_after_from_headers(raw_headers)
            return LLMResponse(
                provider=self.name,
                model=self.model,
                ok=False,
                error=response.text[:500],
                status_code=response.status_code,
                rate_limited=response.status_code == 429,
                retry_after_seconds=retry_after,
                raw_headers=self._safe_headers(raw_headers),
            )
        text = self._extract_text(response.json())
        return LLMResponse(provider=self.name, model=self.model, text=text, ok=bool(text), error=None if text else "empty_response", status_code=response.status_code, raw_headers=self._safe_headers(raw_headers))

    def _gemini_contents(self, messages: list[Message]) -> tuple[str, list[dict]]:
        system_parts = [m.get("content", "") for m in messages if m.get("role") == "system" and m.get("content")]
        system_text = "\n".join(system_parts) or "You are Eva."
        contents = []
        for item in messages:
            role = item.get("role", "user")
            if role == "system":
                continue
            text = str(item.get("content", "")).strip()
            if text:
                contents.append({"role": "model" if role == "assistant" else "user", "parts": [{"text": text}]})
        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})
        return system_text, contents

    def _extract_text(self, data: dict) -> str:
        parts = []
        for candidate in data.get("candidates", []) or []:
            content = candidate.get("content", {}) or {}
            for part in content.get("parts", []) or []:
                if part.get("text"):
                    parts.append(part["text"])
        return "".join(parts).strip()

    def _safe_headers(self, headers: dict[str, str]) -> dict[str, str]:
        keep = {"retry-after", "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset", "x-ratelimit-reset-after"}
        return {k: v for k, v in headers.items() if k in keep}
