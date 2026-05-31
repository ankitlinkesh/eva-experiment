from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.agent.runner import run_agentic_task
from backend.eva.core.config import load_local_env, load_settings
from backend.eva.tools.registry import ToolRegistry
from backend.eva.agent.executor import ToolExecutor


def compact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": result.get("ok"),
        "status": result.get("status"),
        "requires_confirmation": result.get("requires_confirmation"),
        "action": result.get("action"),
        "steps_count": result.get("steps_count"),
        "tools_planned": result.get("tools_planned"),
        "tools_executed": result.get("tools_executed"),
        "safety_stops": result.get("safety_stops"),
        "final_response": result.get("final_response"),
    }


async def run_case(message: str, *, execute_safe: bool, settings, registry: ToolRegistry, executor: ToolExecutor) -> None:
    print(f"\n### {message}")
    result = await run_agentic_task(
        message,
        {
            "settings": settings,
            "registry": registry,
            "executor": executor,
            "execute_tools": execute_safe,
            "history": [],
        },
    )
    print(json.dumps(compact(result), indent=2))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Eva agent runner v1 safely.")
    parser.add_argument("--execute-safe", action="store_true", help="Execute safe whitelisted tools. Power actions still never execute without confirmation.")
    args = parser.parse_args()

    load_local_env(ROOT / ".env")
    settings = load_settings(ROOT / "config" / "eva.toml")
    registry = ToolRegistry()
    executor = ToolExecutor(registry)

    cases = [
        "agent mode: say hello in one sentence",
        "agent mode: find and summarize best github repos for AI agents",
        "agent mode: open chrome",
        "agent mode: shutdown my laptop",
    ]
    for case in cases:
        await run_case(case, execute_safe=args.execute_safe, settings=settings, registry=registry, executor=executor)


if __name__ == "__main__":
    asyncio.run(main())
