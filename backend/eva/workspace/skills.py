from __future__ import annotations

import re
from pathlib import Path

from .config import workspace_status
from .indexer import safe_list_files, search_workspace
from .reader import safe_read_file


FOLDER_DESCRIPTIONS = {
    "backend/eva/api": "FastAPI routes, streaming chat responses, health checks, and UI-facing API glue.",
    "backend/eva/agent": "Planner, executor, bounded agent runner, policies, cognition, task state, and reflection loop.",
    "backend/eva/llm": "Multi-provider LLM router, provider adapters, local rate-limit state, and fallback behavior.",
    "backend/eva/tools": "Whitelisted local tools such as desktop actions, Tavily search, screen capture hooks, and registry definitions.",
    "backend/eva/vision": "On-demand Gemini Vision screen analysis with local rate-limit protection.",
    "frontend": "Browser command center UI, chat stream handling, voice controls, and tool activity display.",
    "scripts": "Verification scripts for planner, router, Tavily, vision, voice, contextual commands, and agent behavior.",
}


def _top_paths(files: list[dict[str, object]], limit: int = 8) -> list[str]:
    return [str(item.get("path") or "") for item in files[:limit] if item.get("path")]


def summarize_file(path: str) -> dict[str, object]:
    read = safe_read_file(path, max_chars=50_000)
    if not read.get("ok"):
        return read
    content = str(read.get("content") or "")
    functions = re.findall(r"^(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)", content, flags=re.MULTILINE)
    classes = re.findall(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", content, flags=re.MULTILINE)
    imports = re.findall(r"^(?:from\s+[^\n]+|import\s+[^\n]+)", content, flags=re.MULTILINE)
    path_obj = Path(str(read.get("path") or path))
    summary_bits = [f"{path_obj.name} is a {path_obj.suffix or 'text'} file with {read.get('line_count')} lines."]
    if classes:
        summary_bits.append("Classes: " + ", ".join(classes[:8]) + ".")
    if functions:
        summary_bits.append("Functions: " + ", ".join(functions[:12]) + ".")
    if imports:
        summary_bits.append("Main imports: " + "; ".join(imports[:6]) + ".")
    return {
        "ok": True,
        "path": read.get("path"),
        "size": read.get("size"),
        "modified_at": read.get("modified_at"),
        "summary": " ".join(summary_bits),
        "classes": classes[:12],
        "functions": functions[:20],
        "truncated": read.get("truncated"),
    }


def summarize_workspace() -> dict[str, object]:
    status = workspace_status()
    if not status.get("enabled"):
        return {"ok": False, "error": "Workspace skills are disabled.", "sections": []}

    sections: list[dict[str, object]] = []
    for folder, description in FOLDER_DESCRIPTIONS.items():
        listed = safe_list_files(folder, limit=40)
        files = listed.get("files") if isinstance(listed, dict) else []
        if not listed.get("ok"):
            sections.append({"folder": folder, "description": description, "ok": False, "error": listed.get("error")})
            continue
        file_items = files if isinstance(files, list) else []
        sections.append(
            {
                "folder": folder,
                "description": description,
                "file_count_sample": len(file_items),
                "notable_files": _top_paths(file_items, 10),
            }
        )

    return {
        "ok": True,
        "root": status.get("root"),
        "sections": sections,
        "safety": "Read-only workspace inspection. Secrets, runtime data, virtualenvs, git internals, logs, and large files are excluded.",
    }
