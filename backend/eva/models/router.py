from __future__ import annotations

from dataclasses import dataclass

from ..core.config import ModelSettings


DEEP_KEYWORDS = {
    "architecture",
    "analyze",
    "bug",
    "build",
    "code",
    "compile",
    "debug",
    "design",
    "error",
    "explain",
    "fix",
    "implement",
    "plan",
    "refactor",
    "stack trace",
    "traceback",
    "why",
}
LOCAL_KEYWORDS = {
    "offline",
    "local only",
    "without internet",
    "use local",
}


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    reason: str


def select_model(message: str, settings: ModelSettings) -> ModelRoute:
    text = message.lower()
    if any(keyword in text for keyword in LOCAL_KEYWORDS):
        if any(keyword in text for keyword in DEEP_KEYWORDS) or len(text) > 700:
            return ModelRoute("ollama", settings.deep_model, "local-deep")
        return ModelRoute("ollama", settings.fast_model, "local-fast")

    if settings.smart_enabled and settings.smart_provider == "gemini":
        return ModelRoute("gemini", settings.smart_model, "smart-cloud")

    if len(text) > 700:
        return ModelRoute("ollama", settings.deep_model, "deep-length")
    if any(keyword in text for keyword in DEEP_KEYWORDS):
        return ModelRoute("ollama", settings.deep_model, "deep-keyword")
    return ModelRoute("ollama", settings.fast_model, "fast-default")
