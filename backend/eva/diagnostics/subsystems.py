from __future__ import annotations

from pathlib import Path
from typing import Any

from ..tools.tavily_search import tavily_status
from ..vision import vision_status


ROOT = Path(__file__).resolve().parents[3]


def _exists(relative: str) -> bool:
    return (ROOT / relative).exists()


def _status_from_exists(relative: str, *, ready: str = "ready") -> str:
    return ready if _exists(relative) else "unavailable"


def get_subsystem_health() -> dict[str, dict[str, Any]]:
    tavily = tavily_status()
    vision = vision_status()
    return {
        "frontend/ui": {
            "status": "ready" if _exists("frontend/app.js") and _exists("frontend/index.html") else "unavailable",
            "notes": "Browser UI, command deck, voice controls, and chat stream files are present.",
        },
        "voice": {
            "status": "ready" if _exists("frontend/app.js") else "unknown",
            "notes": "Voice is browser-side push-to-talk and final-response TTS only.",
        },
        "operator mode": {
            "status": _status_from_exists("backend/eva/core/operator_commands.py"),
            "notes": "Safe deterministic laptop commands route through operator_commands and the tool registry.",
        },
        "Desktop Agent Core": {
            "status": _status_from_exists("backend/eva/desktop/windows.py"),
            "notes": "Window awareness and action verification are available when Windows APIs respond.",
        },
        "Browser Agent Core": {
            "status": _status_from_exists("backend/eva/browser/controller.py"),
            "notes": "Browser state, safe URL opening, page summaries, and research-save hooks are present.",
        },
        "Agentic v2": {
            "status": _status_from_exists("backend/eva/agent/runner.py"),
            "notes": "Bounded plan-act-observe-reflect loop with safety budgets.",
        },
        "code intelligence": {
            "status": _status_from_exists("backend/eva/code/indexer.py"),
            "notes": "Safe code indexing, symbols, project map, traceback debugging, and patch planning.",
        },
        "workspace skills": {
            "status": _status_from_exists("backend/eva/workspace/skills.py"),
            "notes": "Read-only workspace listing/search/reading with secret exclusions.",
        },
        "research SQLite": {
            "status": _status_from_exists("backend/eva/research/store.py"),
            "notes": "Research topics, notes, and sources are stored locally under backend/eva/data.",
        },
        "memory SQLite": {
            "status": _status_from_exists("backend/eva/memory.py") or _status_from_exists("backend/eva/memory"),
            "notes": "Chat/events/facts are local. Secrets are not intentionally exposed.",
        },
        "Tavily/web search": {
            "status": "ready" if tavily.get("configured") else "missing_key",
            "notes": "Tavily gives real web results; browser search remains the fallback.",
        },
        "screen vision": {
            "status": "ready" if vision.get("enabled") and vision.get("configured") else "missing_key" if vision.get("enabled") else "unavailable",
            "notes": "One-shot explicit screen analysis only; no continuous watching.",
        },
        "LLM router": {
            "status": _status_from_exists("backend/eva/llm/router.py"),
            "notes": "Provider fallback, local soft caps, and blocked-provider skipping.",
        },
    }
