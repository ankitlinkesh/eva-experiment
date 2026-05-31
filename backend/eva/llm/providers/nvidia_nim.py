from __future__ import annotations

import os

from ...core.config import ModelSettings
from ._openai_compatible import OpenAICompatibleProvider


DEFAULT_NIM_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
DEFAULT_NIM_FALLBACKS = "openai/gpt-oss-120b,deepseek-ai/deepseek-v4-flash"


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def nvidia_nim_role_models() -> dict[str, str]:
    return {
        "planner": os.environ.get("NVIDIA_NIM_PLANNER_MODEL", DEFAULT_NIM_MODEL).strip() or DEFAULT_NIM_MODEL,
        "deep_reasoning": os.environ.get("NVIDIA_NIM_DEEP_REASONING_MODEL", "nvidia/nemotron-3-super-120b-a12b").strip(),
        "code": os.environ.get("NVIDIA_NIM_CODE_MODEL", "deepseek-ai/deepseek-v4-flash").strip(),
        "vision": os.environ.get("NVIDIA_NIM_VISION_MODEL", "nvidia/nemotron-nano-12b-v2-vl").strip(),
        "screen_reason": os.environ.get("NVIDIA_NIM_SCREEN_REASON_MODEL", "cosmos-reason2-8b").strip(),
        "embed": os.environ.get("NVIDIA_NIM_EMBED_MODEL", "nvidia/llama-nemotron-embed-1b-v2").strip(),
        "rerank": os.environ.get("NVIDIA_NIM_RERANK_MODEL", "nvidia/llama-nemotron-rerank-1b-v2").strip(),
        "safety": os.environ.get("NVIDIA_NIM_SAFETY_MODEL", "nvidia/nemotron-3-content-safety").strip(),
        "pii": os.environ.get("NVIDIA_NIM_PII_MODEL", "nvidia/gliner-pii").strip(),
        "asr": os.environ.get("NVIDIA_NIM_ASR_MODEL", "nvidia/parakeet-tdt-0.6b-v2").strip(),
        "tts": os.environ.get("NVIDIA_NIM_TTS_MODEL", "nvidia/magpie-tts-zeroshot").strip(),
    }


def nvidia_nim_models_for_purpose(purpose: str = "planner") -> list[str]:
    roles = nvidia_nim_role_models()
    primary = os.environ.get("NVIDIA_NIM_MODEL", DEFAULT_NIM_MODEL).strip() or DEFAULT_NIM_MODEL
    purpose_key = purpose.strip().lower()
    role_model = ""
    if purpose_key == "planner":
        role_model = roles["planner"]
    elif purpose_key in {"code", "workspace", "workspace_summary"}:
        role_model = roles["code"]
    elif purpose_key in {"vision", "screen", "screen_reason"}:
        role_model = roles["vision"]
    elif purpose_key in {"deep_reasoning", "debug"}:
        role_model = roles["deep_reasoning"]
    models = [role_model, primary, *_csv(os.environ.get("NVIDIA_NIM_FALLBACK_MODELS", DEFAULT_NIM_FALLBACKS))]
    deduped: list[str] = []
    for model in models:
        if model and model not in deduped:
            deduped.append(model)
    return deduped


class NvidiaNIMProvider(OpenAICompatibleProvider):
    name = "nvidia_nim"
    api_key_env = "NVIDIA_NIM_API_KEY"
    model_env = "NVIDIA_NIM_MODEL"
    default_model = DEFAULT_NIM_MODEL
    base_url_env = "NVIDIA_NIM_BASE_URL"
    default_base_url = "https://integrate.api.nvidia.com/v1"

    def __init__(self, settings: ModelSettings, model: str | None = None) -> None:
        super().__init__(settings)
        if model:
            self.model = model
