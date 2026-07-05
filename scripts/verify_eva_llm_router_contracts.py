from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.llm.formatter import format_llm_fallback_policy, format_llm_limits, format_llm_providers, format_llm_readiness, format_llm_route_preview, format_llm_routing_policy, format_llm_status, format_llm_structured_output
    from backend.eva.llm.provider_contracts import list_provider_contracts
    from backend.eva.llm.router import preview_llm_route
    from backend.eva.llm.status import get_llm_router_status
    from backend.eva.llm.structured_output import validate_mock_structured_output
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.tools.registry import ToolRegistry
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    status = get_llm_router_status()
    assert_true(status.live_calls_enabled is False, "Phase 15A must not enable live calls")
    assert_true({item.provider.value for item in list_provider_contracts()} == {"gemini", "groq", "openrouter", "claude", "ollama", "mock"}, "provider contracts incomplete")
    decision = preview_llm_route("summarize this safely")
    assert_true(decision.live_call_allowed is False and decision.selected_provider.value == "mock", "route preview enabled live provider")
    assert_true(validate_mock_structured_output({"answer": "safe"}).valid, "valid mock output rejected")
    assert_true(not validate_mock_structured_output({"answer": ""}).valid, "invalid mock output accepted")
    outputs = [format_llm_status(), format_llm_providers(), format_llm_routing_policy(), format_llm_fallback_policy(), format_llm_limits(), format_llm_structured_output(), format_llm_route_preview("summarize this safely"), format_llm_readiness()]
    for output in outputs:
        assert_true("{'" not in output and "Traceback" not in output and "C:\\Users\\" not in output, "LLM formatter leaked raw/internal output")
        assert_true("live" in output.lower() and ("locked" in output.lower() or "not enabled" in output.lower()), "LLM formatter missing live-call lock")
    for command in ("eva llm status", "eva llm providers", "eva llm routing policy", "eva llm fallback policy", "eva llm limits", "eva llm structured output", "eva llm route preview summarize this safely", "eva llm readiness", "eva ask what LLMs can Eva use", "eva ask can Eva call the LLM now", "eva ask what happens if the LLM fails", "eva ask show structured output rules"):
        result = maybe_handle_fast_command(command, ToolRegistry())
        assert_true(result is not None and "{'" not in result[0], f"unhandled or unsafe command: {command}")
    for prompt, intent in {"what LLMs can Eva use": "llm_providers", "can Eva call the LLM now": "llm_status", "what happens if the LLM fails": "llm_fallback_policy", "show structured output rules": "llm_structured_output"}.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == intent and route.authority_category == "read" and not route.real_execution_requested, f"wrong LLM route: {prompt}")
    for capability_id in ("llm.status", "llm.providers", "llm.routing_policy", "llm.fallback_policy", "llm.limits", "llm.structured_output", "llm.route_preview", "llm.readiness"):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        assert_true(get_capability_permission(capability_id).read_only, f"capability not read-only {capability_id}")
        assert_true(resolve_capability(capability_id).resource_id == "eva-llm-router-contracts", f"resource mapping missing {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"schema missing {capability_id}")
    assert_true("LLM Router Status" in format_control_center_text(), "Control Center missing LLM panel")
    assert_true("llm.status" in select_capabilities_for_goal("show LLM router status"), "planner selector missing LLM status")
    assert_true(any(step.capability_id == "llm.status" for step in create_task_plan("show LLM router status").steps), "planner decomposer missing LLM status")
    assert_true("LLM Router contract route" in format_team_review("show LLM router status"), "team review missing LLM route")
    source = "\n".join(path.read_text(encoding="utf-8").lower() for path in (ROOT / "backend/eva/llm").glob("*.py") if path.name not in {"router.py", "types.py", "rate_limiter.py"})
    for token in ("requests.", "httpx.", "urllib.request", "pip install", "import playwright", "import pyautogui", "subprocess."):
        assert_true(token not in source, f"forbidden Phase 15A code: {token}")
    print("verify_eva_llm_router_contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
