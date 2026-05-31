from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.agent.runner import run_agentic_task
from backend.eva.core.config import load_local_env, load_settings
from backend.eva.core.fast_commands import maybe_handle_fast_command
from backend.eva.memory.store import MemoryStore
from backend.eva.tools.registry import ToolRegistry
from backend.eva.agent.executor import ToolExecutor


class DryRegistry(ToolRegistry):
    def run(self, name: str, **kwargs: Any) -> Any:
        if name == "web_search":
            return {
                "ok": True,
                "provider": "tavily",
                "query": kwargs.get("query", ""),
                "answer": "Mocked current search answer.",
                "results": [
                    {"title": "OpenHuman", "url": "https://github.com/tinyhumansai/openhuman", "content": "Agent repo.", "score": 0.9},
                    {"title": "LangGraph", "url": "https://github.com/langchain-ai/langgraph", "content": "Agent orchestration.", "score": 0.8},
                ],
            }
        if name == "open_app":
            return f"Opening {kwargs.get('app') or kwargs.get('app_name')}."
        return super().run(name, **kwargs)


def emit(case: str, passed: bool, **payload: object) -> int:
    print(json.dumps({"case": case, "pass": passed, **payload}, indent=2, ensure_ascii=False))
    return 0 if passed else 1


async def main() -> int:
    load_local_env(ROOT / ".env")
    settings = load_settings(ROOT / "config" / "eva.toml")
    registry = DryRegistry()
    executor = ToolExecutor(registry)
    failures = 0

    result = await run_agentic_task(
        "agent mode: find and summarize best github repos for AI agents",
        {"settings": settings, "registry": registry, "executor": executor, "execute_tools": True, "history": []},
    )
    task = result.get("task") or {}
    failures += emit(
        "agent_task_has_plan_and_reflection",
        bool(task.get("plan"))
        and bool(task.get("reflections"))
        and result.get("status") == "done"
        and "web_search" in (result.get("tools_executed") or []),
        status=result.get("status"),
        plan=task.get("plan"),
        reflections=task.get("reflections"),
        final_response=result.get("final_response"),
    )

    result = await run_agentic_task(
        "agent mode: shutdown my laptop",
        {"settings": settings, "registry": registry, "executor": executor, "execute_tools": True, "history": []},
    )
    failures += emit(
        "power_action_requires_confirmation",
        result.get("requires_confirmation") is True and result.get("status") == "waiting_for_confirmation",
        status=result.get("status"),
        action=result.get("action"),
        final_response=result.get("final_response"),
    )

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        memory = MemoryStore(Path(tmp) / "eva-test.sqlite3")
        remember = maybe_handle_fast_command("remember that my favorite test color is cyan", registry, memory=memory, session_id="test")
        about = maybe_handle_fast_command("what do u know abt me", registry, memory=memory, session_id="test")
        facts = memory.recent_memories(limit=3)
        failures += emit(
            "sqlite_memory_fact_roundtrip",
            remember is not None
            and about is not None
            and any("favorite test color is cyan" in item.get("value", "") for item in facts)
            and "favorite test color is cyan" in about[0],
            remember=remember,
            about=about,
            facts=facts,
        )

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
