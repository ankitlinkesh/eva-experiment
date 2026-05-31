from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    api_key_env = "GROQ_API_KEY"
    model_env = "GROQ_MODEL"
    default_model = "llama-3.3-70b-versatile"
    base_url_env = "GROQ_BASE_URL"
    default_base_url = "https://api.groq.com/openai/v1"


class GroqEmergencyProvider(OpenAICompatibleProvider):
    name = "groq"
    api_key_env = "GROQ_API_KEY"
    model_env = "GROQ_FALLBACK_MODEL"
    default_model = "llama-3.1-8b-instant"
    base_url_env = "GROQ_BASE_URL"
    default_base_url = "https://api.groq.com/openai/v1"
