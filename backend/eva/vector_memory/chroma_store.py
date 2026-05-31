from __future__ import annotations

from pathlib import Path

from ..runtime.feature_flags import get_v2_feature_flags


CHROMA_PATH = Path(__file__).resolve().parents[1] / "data" / "vector" / "chroma"


def is_chroma_available() -> bool:
    try:
        import chromadb  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def chroma_status() -> dict[str, object]:
    flags = get_v2_feature_flags()
    available = is_chroma_available()
    return {
        "ok": True,
        "backend": "chroma",
        "available": available,
        "enabled": bool(flags.vector_memory_enabled and available),
        "path": str(CHROMA_PATH),
    }
