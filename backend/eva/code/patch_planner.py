from __future__ import annotations

from typing import Any

from .indexer import search_code


def _likely_files(goal: str) -> list[str]:
    text = goal.lower()
    hints: list[str] = []
    if "browser" in text or "page" in text or "url" in text:
        hints.extend(["backend/eva/browser", "backend/eva/core/fast_commands.py", "backend/eva/tools/registry.py", "scripts/verify_browser_agent_core.py"])
    if "nim" in text or "nvidia" in text:
        hints.extend(["backend/eva/llm/providers/nvidia_nim.py", "backend/eva/llm/router.py", "backend/eva/core/fast_commands.py", "scripts/verify_nvidia_nim_provider.py"])
    if "research" in text:
        hints.extend(["backend/eva/research", "backend/eva/tools/registry.py", "scripts/verify_research_knowledge.py"])
    if "voice" in text or "mic" in text:
        hints.extend(["frontend/app.js", "frontend/index.html", "frontend/styles.css", "scripts/verify_voice_ui.py"])
    if "screen" in text or "vision" in text:
        hints.extend(["backend/eva/vision/screen_vision.py", "backend/eva/tools/registry.py", "scripts/verify_screen_vision.py"])
    for match in search_code(goal, limit=8).get("matches", []):
        if isinstance(match, dict) and match.get("path"):
            hints.append(str(match["path"]))
    deduped: list[str] = []
    for path in hints:
        if path not in deduped:
            deduped.append(path)
    return deduped[:12]


def plan_code_change(goal: str) -> dict[str, Any]:
    clean = " ".join((goal or "").strip().split())
    if not clean:
        return {"ok": False, "error": "Change goal is empty."}
    files = _likely_files(clean)
    return {
        "ok": True,
        "goal": clean,
        "mode": "read_only_patch_plan",
        "approval_required_for_edits": True,
        "likely_files": files,
        "why_these_files": [
            "They match the requested feature keywords or are central shared routing/tool surfaces.",
            "Verifier scripts are included so the change can be tested without relying on vibes.",
        ],
        "proposed_steps": [
            "Inspect the likely files and current tests first.",
            "Patch the smallest shared surface that owns the behavior.",
            "Add or update a dedicated verifier for the feature.",
            "Run compileall plus the targeted verifier scripts.",
            "Manual-test the UI route if the behavior is user-facing.",
        ],
        "tests_to_run": [
            ".\\.venv\\Scripts\\python.exe -m compileall backend",
            ".\\.venv\\Scripts\\python.exe scripts\\verify_agentic_v2.py",
            ".\\.venv\\Scripts\\python.exe scripts\\verify_operator_commands.py",
        ],
        "risks": [
            "Shared routing changes can accidentally steal commands from deterministic handlers.",
            "LLM/provider changes must never expose keys or loop on blocked providers.",
            "Frontend changes can push the chat input off-screen if panel min-height rules regress.",
        ],
        "rollback_note": "Because this is planning-only, rollback means no files are edited yet. If edits are later made, revert only the files touched by that patch.",
    }
