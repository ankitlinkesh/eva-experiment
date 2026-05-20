from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.agent.executor import ToolExecutor
from backend.eva.agent.planner import ToolCallPlanner
from backend.eva.core.config import load_local_env, load_settings
from backend.eva.core.fast_commands import maybe_handle_fast_command
from backend.eva.tools.registry import ToolRegistry


MESSAGES = [
    "status",
    "open chrome",
    "open downloads folder",
    "search web for best AI agent github repos",
    "look at my screen and tell me what error this is",
    "shutdown my laptop",
    "who are you",
]


async def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Eva planner decisions.")
    parser.add_argument("--execute-safe", action="store_true", help="Execute only safe planned tools.")
    args = parser.parse_args()

    load_local_env(ROOT / ".env")
    settings = load_settings(ROOT / "config" / "eva.toml")
    registry = ToolRegistry()
    planner = ToolCallPlanner(settings.models, registry)
    executor = ToolExecutor(registry)

    for message in MESSAGES:
        print(f"\n### {message}")
        informational_fast = message in {"status", "who are you"}
        fast = maybe_handle_fast_command(message, registry) if informational_fast else None
        if fast is not None:
            print(json.dumps({"path": "deterministic", "reply": fast[0], "source": fast[1]}, indent=2))
            continue

        decision = await planner.plan(message, history=[])
        payload = {
            "type": decision.type,
            "reason": decision.reason,
            "tool_calls": [{"tool": call.tool, "args": call.args} for call in decision.tool_calls],
            "final_response": decision.final_response,
            "requires_confirmation": decision.requires_confirmation,
            "action": decision.action,
        }
        print(json.dumps(payload, indent=2))

        if args.execute_safe and decision.type == "tool_calls":
            safe_calls = []
            for call in decision.tool_calls:
                spec = registry.get(call.tool)
                if spec and spec.safety_level == "safe":
                    safe_calls.append(call)
            results = [result.as_dict() for result in executor.execute_all(safe_calls)]
            print(json.dumps({"executed_safe_results": results}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())


