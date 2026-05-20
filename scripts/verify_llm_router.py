from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.eva.agent.planner import ToolCallPlanner
from backend.eva.core.config import load_local_env, load_settings
from backend.eva.llm.router import attempts_as_dicts, complete_with_fallback, get_llm_status
from backend.eva.tools.registry import ToolRegistry


def compact_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "provider": item.get("provider"),
            "model": item.get("model"),
            "ok": item.get("ok"),
            "error": item.get("error"),
            "status_code": item.get("status_code"),
            "rate_limited": item.get("rate_limited"),
            "selected_provider": item.get("selected_provider"),
        }
        for item in attempts
    ]


def decision_to_dict(decision) -> dict[str, Any]:
    return {
        "type": decision.type,
        "reason": decision.reason,
        "tool_calls": [{"tool": call.tool, "args": call.args} for call in decision.tool_calls],
        "final_response": decision.final_response,
        "requires_confirmation": decision.requires_confirmation,
        "action": decision.action,
    }


async def planner_case(planner: ToolCallPlanner, message: str) -> None:
    print(f"\n### planner: {message}")
    try:
        decision = await planner.plan(message, history=[])
        payload = decision_to_dict(decision)
        payload["planner_json_valid"] = True
        payload["providers_tried"] = compact_attempts(planner.last_llm_attempts)
        payload["selected_provider"] = next((a.get("selected_provider") for a in planner.last_llm_attempts if a.get("selected_provider")), "local_fallback")
        payload["fallback_occurred"] = len(planner.last_llm_attempts) > 1 or payload["selected_provider"] == "local_fallback"
        print(json.dumps(payload, indent=2))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "providers_tried": compact_attempts(planner.last_llm_attempts)}, indent=2))


async def router_case(settings, label: str, messages: list[dict[str, str]], purpose: str) -> None:
    print(f"\n### router: {label}")
    routed = await complete_with_fallback(messages, settings.models, purpose=purpose, temperature=0.1, max_tokens=200)
    planner_json_valid = None
    if purpose == "planner" and routed.response.text:
        try:
            json.loads(routed.response.text.strip())
            planner_json_valid = True
        except json.JSONDecodeError:
            planner_json_valid = False
    print(json.dumps({
        "ok": routed.response.ok,
        "selected_provider": routed.response.provider if routed.response.ok else None,
        "selected_model": routed.response.model if routed.response.ok else None,
        "fallback_occurred": routed.fallback_occurred,
        "planner_json_valid": planner_json_valid,
        "providers_tried": compact_attempts(attempts_as_dicts(routed.attempts)),
        "error": routed.response.error,
        "text_preview": routed.response.text[:180],
    }, indent=2))


async def main() -> None:
    load_local_env(ROOT / ".env")
    settings = load_settings(ROOT / "config" / "eva.toml")
    registry = ToolRegistry()
    planner = ToolCallPlanner(settings.models, registry)

    print("### llm status")
    status = get_llm_status(settings.models)
    print(json.dumps({
        "provider_order": status["provider_order"],
        "configured_keys": status["configured_keys"],
        "models": status["models"],
        "blocked_providers": status["blocked_providers"],
        "last_errors": status["last_errors"],
    }, indent=2))

    await planner_case(planner, "open chrome")
    await planner_case(planner, "search web for best github repos for AI agents")
    await router_case(settings, "say hello in one sentence", [{"role": "user", "content": "Say hello in one short sentence."}], "final_response")
    await router_case(settings, "invalid planner JSON handling", [{"role": "user", "content": "Return plain English, not JSON: hello"}], "planner")

    original = os.environ.get("EVA_ALLOW_CLOUD_FALLBACK")
    os.environ["EVA_ALLOW_CLOUD_FALLBACK"] = "false"
    local_only = ToolCallPlanner(settings.models, registry)
    await planner_case(local_only, "open downloads folder")
    if original is None:
        os.environ.pop("EVA_ALLOW_CLOUD_FALLBACK", None)
    else:
        os.environ["EVA_ALLOW_CLOUD_FALLBACK"] = original


if __name__ == "__main__":
    asyncio.run(main())
