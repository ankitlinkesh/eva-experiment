from __future__ import annotations

from typing import Any

from .feature_flags import get_v2_feature_flags
from .nodes import run_fallback_nodes


def is_langgraph_available() -> bool:
    try:
        import langgraph  # type: ignore  # noqa: F401
    except Exception:
        return False
    return True


def build_eva_v2_graph() -> dict[str, Any]:
    flags = get_v2_feature_flags()
    if flags.langgraph_enabled and is_langgraph_available():
        return {"ok": True, "runtime": "langgraph", "compiled": False, "message": "LangGraph is available; Phase 1 exposes a compatible skeleton only."}
    return {"ok": True, "runtime": "fallback_sequential", "compiled": True, "message": "LangGraph unavailable or disabled; using deterministic fallback nodes."}


def run_eva_v2_request(user_request: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    graph = build_eva_v2_graph()
    state = run_fallback_nodes(user_request, context=context)
    flags = get_v2_feature_flags()
    return {
        "ok": True,
        "runtime": graph["runtime"],
        "enabled": flags.runtime_enabled,
        "delegated": not flags.runtime_enabled,
        "state": state.as_dict(),
    }
