from __future__ import annotations

from ..runtime.feature_flags import get_v2_feature_flags


def is_langfuse_available() -> bool:
    try:
        import langfuse  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def langfuse_status() -> dict[str, object]:
    flags = get_v2_feature_flags()
    available = is_langfuse_available()
    enabled = bool(flags.langfuse_enabled and available)
    return {
        "ok": True,
        "available": available,
        "enabled": enabled,
        "message": "Langfuse adapter is disabled unless EVA_V2_LANGFUSE_ENABLED=true and the package is installed.",
    }
