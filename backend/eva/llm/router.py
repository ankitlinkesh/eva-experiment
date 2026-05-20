from __future__ import annotations

import json
import os
import time
from typing import Iterable

from ..core.config import ModelSettings
from .providers.clod import ClodProvider
from .providers.gemini import GeminiProvider
from .providers.groq import GroqEmergencyProvider, GroqProvider
from .providers.ollama import OllamaProvider
from .providers.openrouter import OpenRouterProvider
from .rate_limiter import LLMRateLimiter, provider_limits
from .types import LLMAttempt, LLMProvider, LLMResponse, Message, RoutedLLMResponse

DEFAULT_PROVIDER_ORDER = ["gemini", "groq", "openrouter", "clod"]
PROVIDER_CLASSES = {
    "gemini": GeminiProvider,
    "groq": GroqProvider,
    "openrouter": OpenRouterProvider,
    "clod": ClodProvider,
    "ollama": OllamaProvider,
}


def provider_order() -> list[str]:
    raw = os.environ.get("EVA_CLOUD_PROVIDER_ORDER", "gemini,groq,openrouter,clod")
    allow_cloud = os.environ.get("EVA_ALLOW_CLOUD_FALLBACK", "true").strip().lower() not in {"0", "false", "no", "off"}
    names = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not names:
        names = list(DEFAULT_PROVIDER_ORDER)
    deduped: list[str] = []
    for name in names:
        if name in PROVIDER_CLASSES and name != "ollama" and name not in deduped:
            deduped.append(name)
    ordered = deduped if allow_cloud else []
    if "ollama" not in ordered:
        ordered.append("ollama")
    return ordered


def build_provider(name: str, settings: ModelSettings) -> LLMProvider | None:
    cls = PROVIDER_CLASSES.get(name)
    return cls(settings) if cls else None


def _is_retryable_failure(response: LLMResponse) -> bool:
    if response.ok and response.text.strip():
        return False
    if response.rate_limited:
        return True
    if response.status_code is None:
        return True
    if response.status_code >= 500:
        return True
    if response.error in {"empty_response", "missing_api_key"}:
        return True
    return False


def _json_is_valid(text: str) -> bool:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").removeprefix("json").strip()
    try:
        json.loads(cleaned)
        return True
    except json.JSONDecodeError:
        return False


def _attempt_from_response(response: LLMResponse, purpose: str, *, selected_provider: str | None = None, fallback_used: bool = False) -> LLMAttempt:
    return LLMAttempt(
        provider=response.provider,
        model=response.model,
        purpose=purpose,
        ok=response.ok,
        error=response.error,
        status_code=response.status_code,
        rate_limited=response.rate_limited,
        fallback_used=fallback_used,
        selected_provider=selected_provider,
    )


async def complete_with_fallback(
    messages: list[Message],
    settings: ModelSettings,
    *,
    purpose: str = "planner",
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> RoutedLLMResponse:
    limiter = LLMRateLimiter()
    attempts: list[LLMAttempt] = []
    tried_cloud_count = 0

    for name in provider_order():
        provider = build_provider(name, settings)
        if provider is None:
            continue

        if not provider.available():
            response = LLMResponse(provider=name, model=getattr(provider, "model", ""), ok=False, error="missing_api_key")
            attempts.append(_attempt_from_response(response, purpose, fallback_used=bool(attempts)))
            continue

        allowed, reason = limiter.can_call(name)
        if not allowed:
            response = LLMResponse(provider=name, model=getattr(provider, "model", ""), ok=False, error=reason)
            attempts.append(_attempt_from_response(response, purpose, fallback_used=bool(attempts)))
            continue

        if name != "ollama":
            tried_cloud_count += 1

        response = await provider.complete(messages, temperature=temperature, max_tokens=max_tokens)
        if response.ok:
            limiter.record_success(name)
        else:
            limiter.record_failure(name, response.error or "unknown_error", rate_limited=response.rate_limited, retry_after_seconds=response.retry_after_seconds)

        if response.ok and purpose == "planner" and not _json_is_valid(response.text):
            response = LLMResponse(
                provider=response.provider,
                model=response.model,
                text=response.text,
                ok=False,
                error="invalid_planner_json",
                status_code=response.status_code,
                rate_limited=False,
                raw_headers=response.raw_headers,
            )
            limiter.record_failure(name, "invalid_planner_json")

        if response.ok and response.text.strip():
            selected = response.provider
            attempts.append(_attempt_from_response(response, purpose, selected_provider=selected, fallback_used=bool(attempts)))
            return RoutedLLMResponse(response=response, attempts=attempts, fallback_occurred=len(attempts) > 1)

        attempts.append(_attempt_from_response(response, purpose, fallback_used=bool(attempts)))

        if name == "groq" and provider.model == os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile") and _is_retryable_failure(response):
            emergency = GroqEmergencyProvider(settings)
            if emergency.available() and emergency.model != provider.model:
                allowed, reason = limiter.can_call("groq")
                if allowed:
                    emergency_response = await emergency.complete(messages, temperature=temperature, max_tokens=max_tokens)
                    if emergency_response.ok:
                        limiter.record_success("groq")
                    else:
                        limiter.record_failure("groq", emergency_response.error or "unknown_error", rate_limited=emergency_response.rate_limited, retry_after_seconds=emergency_response.retry_after_seconds)
                    if emergency_response.ok and purpose == "planner" and not _json_is_valid(emergency_response.text):
                        emergency_response = LLMResponse(provider="groq", model=emergency.model, text=emergency_response.text, ok=False, error="invalid_planner_json", status_code=emergency_response.status_code)
                    if emergency_response.ok and emergency_response.text.strip():
                        attempts.append(_attempt_from_response(emergency_response, purpose, selected_provider="groq", fallback_used=True))
                        return RoutedLLMResponse(response=emergency_response, attempts=attempts, fallback_occurred=True)
                    attempts.append(_attempt_from_response(emergency_response, purpose, fallback_used=True))
                else:
                    attempts.append(LLMAttempt(provider="groq", model=emergency.model, purpose=purpose, ok=False, error=reason, fallback_used=True))

    final_error = "; ".join(f"{attempt.provider}:{attempt.error or attempt.status_code}" for attempt in attempts[-4:]) or "no_provider_available"
    return RoutedLLMResponse(
        response=LLMResponse(provider="none", model="none", ok=False, error=final_error),
        attempts=attempts,
        fallback_occurred=bool(attempts),
    )


def _env_has_key(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def get_llm_status(settings: ModelSettings | None = None) -> dict:
    settings = settings or ModelSettings()
    limiter = LLMRateLimiter()
    usage = limiter.status()
    models = {
        "gemini": os.environ.get("GEMINI_MODEL", settings.smart_model or "gemini-2.5-flash"),
        "groq": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "groq_fallback": os.environ.get("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant"),
        "openrouter": os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free"),
        "clod": os.environ.get("CLOD_MODEL", "DeepSeek V3"),
        "ollama": settings.fast_model or settings.ollama_model,
    }
    keys = {
        "gemini": _env_has_key("GEMINI_API_KEY"),
        "groq": _env_has_key("GROQ_API_KEY"),
        "openrouter": _env_has_key("OPENROUTER_API_KEY"),
        "clod": _env_has_key("CLOD_API_KEY"),
        "ollama": True,
    }
    now = int(time.time())
    blocked = {
        provider: int(entry.get("blocked_until") or 0)
        for provider, entry in usage.items()
        if int(entry.get("blocked_until") or 0) > now
    }
    last_errors = {provider: entry.get("last_error") for provider, entry in usage.items() if entry.get("last_error")}
    limits = {provider: {"soft_rpm": provider_limits(provider)[0], "soft_rpd": provider_limits(provider)[1]} for provider in ["gemini", "groq", "openrouter", "clod"]}
    return {
        "provider_order": provider_order(),
        "configured_keys": keys,
        "models": models,
        "usage": usage,
        "blocked_providers": blocked,
        "last_errors": last_errors,
        "limits": limits,
        "allow_cloud_fallback": os.environ.get("EVA_ALLOW_CLOUD_FALLBACK", "true").strip().lower() not in {"0", "false", "no", "off"},
    }


def attempts_as_dicts(attempts: Iterable[LLMAttempt]) -> list[dict]:
    return [attempt.__dict__.copy() for attempt in attempts]
