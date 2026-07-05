from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CAPABILITIES = ("llm.red_team_status", "llm.red_team_cases", "llm.red_team_run", "llm.failure_tests", "llm.safety_failure_report", "llm.red_team_readiness")


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.agents.team_review import format_team_review
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.collector import collect_control_center_status
    from backend.eva.control_center.formatter import format_control_center_status, render_control_center_html
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.llm.red_team_cases import list_red_team_cases
    from backend.eva.llm.red_team_runner import run_local_red_team
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.tools.registry import ToolRegistry
    from scripts import verify_eva_all

    categories = {case.category for case in list_red_team_cases()}
    required = {"malformed_json", "invalid_enum", "unknown_capability", "hallucinated_capability", "tool_execution", "prompt_injection", "secret_exfiltration", "private_path", "oversized_output", "provider_timeout", "rate_limit_fallback", "degraded_mode", "runaway_loop", "repair_policy_abuse", "command_injection"}
    check(required <= categories, "red-team categories incomplete")
    run = run_local_red_team()
    check(run.total == len(categories) and run.failed_safely == run.total and run.live_calls_enabled is False and run.tool_execution_enabled is False, "red-team runner is unsafe or incomplete")
    for category in required:
        check(any(item.category == category and item.safe for item in run.results), f"unsafe case not blocked: {category}")

    commands = ("eva llm red team status", "eva llm red team cases", "eva llm red team run", "eva llm failure tests", "eva llm safety failure report", "eva llm red team readiness")
    for command in commands:
        result = maybe_handle_fast_command(command, ToolRegistry())
        check(result and "live llm calls: locked" in result[0].lower() and "invalid llm-like output cannot execute tools" in result[0].lower(), f"command missing or unsafe: {command}")
    asks = {"run LLM red team tests": "llm_red_team_run", "show LLM failure tests": "llm_failure_tests", "can unsafe LLM output execute tools": "llm_red_team_status", "what if the LLM leaks secrets": "llm_safety_failure_report", "what if the LLM ignores safety policy": "llm_safety_failure_report", "show LLM red team readiness": "llm_red_team_readiness", "show LLM safety failure report": "llm_safety_failure_report"}
    for prompt, intent in asks.items():
        route = route_natural_request(prompt)
        check(route.intent == intent and not route.real_execution_requested, f"bad ask route: {prompt}")
        result = maybe_handle_fast_command(f"eva ask {prompt}", ToolRegistry())
        check(result and "Eva ask" in result[0], f"ask unavailable: {prompt}")
    status = collect_control_center_status()
    check(status.llm_red_team_summary.get("status") == "available" and "LLM Red-Team / Failure Tests" in format_control_center_status(status) and "LLM Red-Team / Failure Tests" in render_control_center_html(status), "Control Center panel missing")
    for capability_id in CAPABILITIES:
        check(get_capability(capability_id) is not None and resolve_capability(capability_id).preview_only, f"capability mapping missing: {capability_id}")
        schema = capability_to_tool_schema(capability_id)
        check(schema and schema.get("execution_status") == "read_only_metadata" and schema.get("safety_notes"), f"schema missing: {capability_id}")
    check(select_capabilities_for_goal("run LLM red team tests") == ["llm.red_team_run"], "planner red-team route unsafe")
    review = format_team_review("review LLM red team safety")
    for phrase in ("tests are local/mock only", "unsafe LLM-like outputs cannot execute tools", "Phase 16 Context Assembly Engine is next"):
        check(phrase.lower() in review.lower(), f"team review missing: {phrase}")
    for doc in ("EVA_CURRENT_STATE.md", "EVA_CAPABILITIES.md", "EVA_AGENT_FRAMEWORK.md", "EVA_THREAT_MODEL.md", "EVA_VERIFICATION.md"):
        check("Phase 15D" in (ROOT / "docs" / doc).read_text(encoding="utf-8"), f"docs missing Phase 15D: {doc}")
    check("verify_eva_llm_red_team_failure_tests.py" in verify_eva_all.FULL_VERIFIERS and "verify_eva_llm_red_team_failure_tests.py" in verify_eva_all.QUICK_VERIFIERS, "master verifier coverage missing")
    print("PASS: Phase 15D red-team/failure tests are local, safe, and fully wired.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
