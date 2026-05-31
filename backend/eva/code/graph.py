from __future__ import annotations

from collections import Counter
from typing import Any

from .indexer import load_code_index


MODULE_DESCRIPTIONS = {
    "backend/eva/api": "FastAPI routes and chat orchestration.",
    "backend/eva/agent": "Agentic task loop, planner policies, task state, and reusable skills.",
    "backend/eva/llm": "LLM provider router, rate limits, cloud/local fallbacks, and provider clients.",
    "backend/eva/tools": "Safe whitelisted tools, desktop operations, Tavily search, and registry dispatch.",
    "backend/eva/browser": "Browser Agent Core for safe page awareness, opening URLs, searches, summaries, and research saves.",
    "backend/eva/desktop": "Desktop Agent Core for active/open window awareness and action verification.",
    "backend/eva/research": "SQLite-backed local research knowledge, recall, and summarization.",
    "backend/eva/workspace": "Read-only workspace safety, file listing, safe reads, and project summaries.",
    "backend/eva/vision": "On-demand screen analysis and Gemini Vision rate-limit handling.",
    "frontend": "Eva browser UI, chat deck, voice controls, and activity rendering.",
    "scripts": "Verification scripts for each feature family.",
}


def code_project_map() -> dict[str, Any]:
    index = load_code_index()
    if not index.get("ok"):
        return {"ok": False, "error": index.get("error") or "index unavailable", "modules": []}
    files = [item for item in index.get("files", []) if isinstance(item, dict)]
    modules: list[dict[str, Any]] = []
    for prefix, description in MODULE_DESCRIPTIONS.items():
        owned = [item for item in files if str(item.get("path") or "").startswith(prefix)]
        if not owned:
            continue
        symbols = sum(len(item.get("symbols") or []) for item in owned)
        tools = sorted({str(tool) for item in owned for tool in item.get("tool_names", [])})
        imports = Counter(str(dep).split(".")[0] for item in owned for dep in item.get("imports", []) if dep)
        modules.append(
            {
                "folder": prefix,
                "description": description,
                "file_count": len(owned),
                "symbol_count": symbols,
                "tools": tools[:15],
                "top_imports": [name for name, _ in imports.most_common(8)],
                "notable_files": [str(item.get("path")) for item in owned[:8]],
            }
        )
    return {"ok": True, "indexed_files": len(files), "modules": modules}
