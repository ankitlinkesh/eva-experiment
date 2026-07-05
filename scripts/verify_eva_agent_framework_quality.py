from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def emit(case: str, passed: bool, **extra: Any) -> bool:
    import json

    payload = {"case": case, "pass": bool(passed)}
    payload.update(extra)
    print(json.dumps(payload, indent=2, default=str))
    return bool(passed)


def assert_clean_output(text: str) -> tuple[bool, str | None]:
    forbidden = ["{'", "AgentAssignmentQuality(", "AgentTeamReview(", "Traceback", "C:\\Users\\"]
    for marker in forbidden:
        if marker in text:
            return False, marker
    return True, None


def main() -> int:
    checks: list[bool] = []

    try:
        quality = importlib.import_module("backend.eva.agents.quality")
        checks.append(emit("agent_quality_module_imports", True))
    except Exception as exc:
        checks.append(emit("agent_quality_module_imports", False, error=str(exc)))
        return 1

    try:
        team_review = importlib.import_module("backend.eva.agents.team_review")
        checks.append(emit("agent_team_review_module_imports", True))
    except Exception as exc:
        checks.append(emit("agent_team_review_module_imports", False, error=str(exc)))
        return 1

    from backend.eva.agents.delegation import (
        dry_run_plan_with_agents,
        format_agent_dry_run_for_goal,
        validate_agent_dry_run_results,
    )
    from backend.eva.agents.registry import get_agent, get_all_agents, select_agent_for_step
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.planner.decomposer import create_task_plan

    agents = get_all_agents()
    checks.append(emit("agent_registry_non_empty", bool(agents), count=len(agents)))

    research_plan = create_task_plan("use my saved research about Eva")
    research_result = dry_run_plan_with_agents(research_plan)
    research_agents = {response.agent_name for response in research_result.responses}
    checks.append(
        emit(
            "saved_research_plan_assigns_research_or_memory",
            bool({"ResearchAgent", "MemoryAgent"} & research_agents),
            agents=sorted(research_agents),
        )
    )

    whatsapp_plan = create_task_plan("send WhatsApp to mom saying hi")
    whatsapp_result = dry_run_plan_with_agents(whatsapp_plan)
    whatsapp_agents = {response.agent_name for response in whatsapp_result.responses}
    whatsapp_gated = any(
        response.agent_name in {"SafetyAgent", "SupervisorAgent"} and response.required_permission in {"confirmation_required", "blocked"}
        for response in whatsapp_result.responses
    )
    checks.append(emit("whatsapp_plan_safety_or_confirmation", whatsapp_gated, agents=sorted(whatsapp_agents)))

    delete_plan = create_task_plan("delete Downloads folder")
    delete_result = dry_run_plan_with_agents(delete_plan)
    delete_safe = any(
        response.agent_name in {"SafetyAgent", "SupervisorAgent"} and response.required_permission in {"override_required", "blocked", "confirmation_required"}
        for response in delete_result.responses
    )
    checks.append(emit("delete_plan_safety_or_override", delete_safe))

    browser_plan = create_task_plan("open ChatGPT on Chrome")
    browser_result = dry_run_plan_with_agents(browser_plan)
    browser_dry = any(response.agent_name == "BrowserAgent" and response.status in {"dry_run", "refused"} for response in browser_result.responses)
    checks.append(emit("browser_plan_browseragent_dry_run_only", browser_dry))

    unknown_plan = create_task_plan("do the mysterious thing with unknown capability")
    unknown_agent = select_agent_for_step(unknown_plan.steps[-1])
    checks.append(
        emit(
            "unknown_goal_safe_fallback_agent",
            type(unknown_agent).__name__ in {"SupervisorAgent", "SafetyAgent", "PlannerAgent"},
            agent=type(unknown_agent).__name__,
        )
    )

    coverage = quality.evaluate_plan_agent_coverage(research_plan, research_result.responses)
    checks.append(
        emit(
            "coverage_score_between_zero_and_one",
            0.0 <= coverage.coverage_score <= 1.0,
            score=coverage.coverage_score,
            coverage_passed=coverage.passed,
        )
    )

    coverage_text = quality.format_agent_coverage_report(coverage)
    clean, marker = assert_clean_output(coverage_text)
    checks.append(emit("agent_coverage_report_human_readable", clean and "Agent coverage report" in coverage_text, marker=marker, output=coverage_text))

    review = team_review.review_plan_with_agent_team(whatsapp_plan)
    review_text = team_review.format_agent_team_review(review)
    clean, marker = assert_clean_output(review_text)
    checks.append(emit("agent_team_review_human_readable", clean and "Agent team review" in review_text, marker=marker, output=review_text))

    simulated_validation = validate_agent_dry_run_results(research_plan, research_result.responses[:-1])
    checks.append(
        emit(
            "dry_run_validation_catches_missing_result",
            bool(simulated_validation.blockers),
            blockers=simulated_validation.blockers,
        )
    )

    risk_not_executed = all(response.status != "executed" for response in delete_result.responses + whatsapp_result.responses)
    checks.append(emit("risky_steps_not_marked_executed", risk_not_executed))

    request = browser_result.responses[0]
    browser_execute = get_agent("BrowserAgent").execute(request)
    desktop_execute = get_agent("DesktopAgent").execute(request)
    checks.append(emit("browseragent_execute_refused", browser_execute.status == "refused", response=browser_execute.as_dict()))
    checks.append(emit("desktopagent_execute_refused", desktop_execute.status == "refused", response=desktop_execute.as_dict()))

    commands = [
        "eva agents review plan use my saved research about Eva",
        "eva agents review plan send WhatsApp to mom saying hi",
        "eva agents coverage delete Downloads folder",
        "eva agents validate plan open ChatGPT on Chrome",
    ]
    for command in commands:
        reply = maybe_handle_fast_command(command, None, None, [])
        text = reply[0] if reply else ""
        clean, marker = assert_clean_output(text)
        checks.append(emit(f"command_{command.replace(' ', '_')}", bool(reply) and clean, marker=marker, output=text))

    dry_run_text = format_agent_dry_run_for_goal("send WhatsApp to mom saying hi")
    checks.append(emit("dry_run_output_mentions_team_review", "Team review:" in dry_run_text, output=dry_run_text))

    forbidden_scan_roots = [ROOT / "backend" / "eva" / "agents"]
    forbidden_terms = [
        "import playwright",
        "from playwright",
        "import pyautogui",
        "from pyautogui",
        "mcp.run",
        "subprocess.",
        "open('.env.local",
        'open(".env.local',
        "shell_command",
    ]
    hits: list[str] = []
    for scan_root in forbidden_scan_roots:
        for path in scan_root.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            for term in forbidden_terms:
                if term in text.lower():
                    hits.append(f"{path.name}:{term}")
    checks.append(emit("agent_framework_no_forbidden_execution_calls", not hits, hits=hits))

    expected_existing_verifiers = [
        "verify_eva_agent_framework_v1.py",
        "verify_eva_planner_v3_quality.py",
        "verify_eva_planner_v3.py",
        "verify_eva_capability_resource_mapping.py",
        "verify_eva_capability_permissions.py",
        "verify_eva_stabilization_v1.py",
    ]
    missing = [name for name in expected_existing_verifiers if not (ROOT / "scripts" / name).exists()]
    checks.append(emit("existing_verifiers_available_for_sequential_sweep", not missing, missing=missing))

    passed = all(checks)
    emit("overall_pass", passed, failures=checks.count(False))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
