from __future__ import annotations

from typing import Any

from .debugger import debug_traceback
from .graph import code_project_map
from .indexer import build_code_index, code_status, search_code
from .patch_planner import plan_code_change
from .symbols import find_symbol


def code_explain_feature(feature: str) -> dict[str, Any]:
    query = " ".join((feature or "").strip().split())
    if not query:
        return {"ok": False, "error": "Feature query is empty."}
    matches = search_code(query, limit=10)
    related = matches.get("matches", []) if matches.get("ok") else []
    files = [str(item.get("path")) for item in related if isinstance(item, dict) and item.get("path")]
    lowered = query.lower()
    hints: list[str] = []
    if "browser" in lowered:
        hints.extend(["backend/eva/browser", "scripts/verify_browser_agent_core.py", "backend/eva/core/fast_commands.py", "backend/eva/tools/registry.py"])
    if "desktop" in lowered:
        hints.extend(["backend/eva/desktop", "scripts/verify_desktop_agent_core.py", "backend/eva/core/fast_commands.py", "backend/eva/tools/registry.py"])
    if "nim" in lowered or "nvidia" in lowered:
        hints.extend(["backend/eva/llm/providers/nvidia_nim.py", "backend/eva/llm/router.py", "scripts/verify_nvidia_nim_provider.py"])
    if "research" in lowered:
        hints.extend(["backend/eva/research", "scripts/verify_research_knowledge.py", "backend/eva/tools/registry.py"])
    for hint in reversed(hints):
        if hint not in files:
            files.insert(0, hint)
    return {
        "ok": True,
        "feature": query,
        "related_files": files[:10],
        "summary": f"I found {len(files)} likely code location(s) for {query}. Start with the top files and then run the matching verifier.",
        "matches": related[:10],
        "tests_to_consider": [
            ".\\.venv\\Scripts\\python.exe -m compileall backend",
            ".\\.venv\\Scripts\\python.exe scripts\\verify_agentic_v2.py",
        ],
    }


def code_reindex() -> dict[str, Any]:
    return build_code_index()


def code_search(query: str, limit: int = 10) -> dict[str, Any]:
    return search_code(query, limit=limit)


def code_find_symbol(symbol: str) -> dict[str, Any]:
    return find_symbol(symbol)


def code_debug_traceback(traceback: str) -> dict[str, Any]:
    return debug_traceback(traceback)


def code_plan_change(goal: str) -> dict[str, Any]:
    return plan_code_change(goal)


def code_status_tool() -> dict[str, Any]:
    return code_status()


def code_project_map_tool() -> dict[str, Any]:
    return code_project_map()
