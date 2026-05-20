from __future__ import annotations

from ._openai_compatible import OpenAICompatibleProvider


class ClodProvider(OpenAICompatibleProvider):
    name = "clod"
    api_key_env = "CLOD_API_KEY"
    model_env = "CLOD_MODEL"
    default_model = "DeepSeek V3"
    base_url_env = "CLOD_BASE_URL"
    default_base_url = "https://api.clod.io/v1"
