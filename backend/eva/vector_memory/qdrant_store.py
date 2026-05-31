from __future__ import annotations

from ..runtime.feature_flags import get_v2_feature_flags


def is_qdrant_available() -> bool:
    try:
        import qdrant_client  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def qdrant_status() -> dict[str, object]:
    flags = get_v2_feature_flags()
    available = is_qdrant_available()
    return {
        "ok": True,
        "backend": "qdrant",
        "available": available,
        "enabled": bool(flags.vector_memory_enabled and available),
        "message": "Qdrant is interface-ready but not configured as the default local memory store in Phase 1.",
    }
