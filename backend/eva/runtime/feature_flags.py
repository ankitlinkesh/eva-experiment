from __future__ import annotations

import os
from dataclasses import asdict, dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


@dataclass(frozen=True)
class EvaV2FeatureFlags:
    runtime_enabled: bool = False
    langgraph_enabled: bool = False
    llm_guard_enabled: bool = False
    langfuse_enabled: bool = False
    vector_memory_enabled: bool = False
    playwright_enabled: bool = False
    pyautogui_enabled: bool = False

    def as_dict(self) -> dict[str, bool]:
        return asdict(self)


def get_v2_feature_flags() -> EvaV2FeatureFlags:
    return EvaV2FeatureFlags(
        runtime_enabled=_env_bool("EVA_V2_RUNTIME_ENABLED", False),
        langgraph_enabled=_env_bool("EVA_V2_LANGGRAPH_ENABLED", False),
        llm_guard_enabled=_env_bool("EVA_V2_LLM_GUARD_ENABLED", False),
        langfuse_enabled=_env_bool("EVA_V2_LANGFUSE_ENABLED", False),
        vector_memory_enabled=_env_bool("EVA_V2_VECTOR_MEMORY_ENABLED", False),
        playwright_enabled=_env_bool("EVA_V2_PLAYWRIGHT_ENABLED", False),
        pyautogui_enabled=_env_bool("EVA_V2_PYAUTOGUI_ENABLED", False),
    )


def eva_v2_runtime_status() -> dict[str, object]:
    flags = get_v2_feature_flags()
    return {
        "ok": True,
        "installed": True,
        "enabled": flags.runtime_enabled,
        "flags": flags.as_dict(),
        "message": (
            "Eva v2 runtime skeleton is installed and enabled."
            if flags.runtime_enabled
            else "Eva v2 runtime skeleton is installed but disabled. EVA_V2_RUNTIME_ENABLED=false, so current Eva behavior remains active."
        ),
    }
