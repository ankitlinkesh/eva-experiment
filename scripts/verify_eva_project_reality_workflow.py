from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_clean(text: str, label: str) -> None:
    forbidden = [
        "{'",
        "ProjectInspectionResult(",
        "RealityCheckResult(",
        "Traceback",
        "C:\\Users\\",
        ".env.local",
        "api_key",
        "Bearer ",
    ]
    for token in forbidden:
        assert_true(token not in text, f"{label} leaked unsafe/internal token: {token}")


def main() -> int:
    from backend.eva.agents.team_review import format_team_review
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import build_default_registry
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.skills.project_inspection import (
        format_project_inspection,
        format_project_next_step,
        format_recent_project_changes,
        inspect_project_status,
    )
    from backend.eva.skills.reality_check import (
        format_broken_status,
        format_done_check,
        format_project_proof,
        format_reality_check,
    )
    from backend.eva.skills.selector import select_skills_for_request
    from backend.eva.specialists.selector import select_specialists_for_request
    from backend.eva.tools.registry import ToolRegistry

    inspection = inspect_project_status()
    assert_true(inspection.read_only, "project inspection is read-only")
    assert_true("Eva" in inspection.project_summary or "local assistant" in inspection.project_summary, "inspection identifies Eva project")

    outputs = {
        "project inspection": format_project_inspection(inspection),
        "recent changes": format_recent_project_changes(),
        "project next step": format_project_next_step(),
        "reality check": format_reality_check(),
        "done check": format_done_check(),
        "project proof": format_project_proof(),
        "broken status": format_broken_status(),
    }
    for label, text in outputs.items():
        assert_clean(text, label)
        assert_true("Execution: read-only" in text or "No task was executed" in text, f"{label} is framed as non-executing")

    assert_true("Phase 12" in outputs["recent changes"], "recent changes is Phase 12 aware")
    assert_true("Phase 12O" in outputs["recent changes"], "recent changes includes Phase 12O")
    assert_true("not claim done" in outputs["done check"].lower(), "done check does not overclaim")
    assert_true("Evidence" in outputs["project proof"], "proof output has evidence section")
    assert_true("No failing verifier evidence" in outputs["broken status"], "broken status avoids guessing failures")
    assert_true("Phase 12P" in outputs["project next step"] or "next safe phase" in outputs["project next step"].lower(), "next step recommends one safe phase")

    route_expectations = {
        "inspect this project": "project_inspect",
        "explain this repo": "project_inspect",
        "what changed recently": "project_recent_changes",
        "are we actually done": "done_check",
        "what proof do we have": "project_proof",
        "what is broken": "project_broken_status",
        "what should we do next": "project_next_step",
        "summarize current Eva status": "project_inspect",
    }
    for prompt, intent in route_expectations.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == intent, f"{prompt!r} routes to {intent}, got {route.intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} remains read-only")

    tools = ToolRegistry()
    commands = [
        "eva project inspect",
        "eva project reality check",
        "eva project recent changes",
        "eva project next step",
        "eva project proof",
        "eva phase status",
        "eva done check",
        "eva ask inspect this project",
        "eva ask explain this repo",
        "eva ask what changed recently",
        "eva ask are we actually done",
        "eva ask what proof do we have",
        "eva ask what is broken",
        "eva ask what should we do next",
    ]
    for command in commands:
        result = maybe_handle_fast_command(command, tools)
        assert_true(result is not None, f"{command} handled")
        text = result[0]
        assert_clean(text, command)
        assert_true("Authority decision" in text or command.startswith("eva project") or command in {"eva phase status", "eva done check"}, f"{command} has routing/authority context where expected")

    specialists = [item.id for item in select_specialists_for_request("what is broken")]
    assert_true("test_results_analyzer" in specialists, "broken routes to test results analyzer")
    assert_true("reality_checker" in specialists, "broken routes to reality checker")
    next_specialists = [item.id for item in select_specialists_for_request("what should we do next")]
    assert_true("safety_reviewer" in next_specialists and "evidence_collector" in next_specialists, "next step routes to safety/evidence")
    inspect_specialists = [item.id for item in select_specialists_for_request("inspect this project")]
    assert_true("codebase_onboarding_specialist" in inspect_specialists, "inspect routes to onboarding")

    skill_ids = [item.id for item in select_skills_for_request("what proof do we have")]
    assert_true("verification_before_completion" in skill_ids, "proof routes to verification skill")
    inspect_skill_ids = [item.id for item in select_skills_for_request("inspect this project")]
    assert_true("project_inspection_readonly" in inspect_skill_ids, "inspect routes to project inspection skill")

    registry = build_default_registry()
    for cap_id in [
        "eva.project_inspect",
        "eva.project_reality_check",
        "eva.project_recent_changes",
        "eva.project_next_step",
        "eva.project_proof",
        "eva.done_check",
    ]:
        assert_true(registry.get(cap_id) is not None, f"{cap_id} registered")
        permission = get_capability_permission(cap_id)
        assert_true(permission.read_only, f"{cap_id} is read-only")
        assert_true(not permission.external_effect, f"{cap_id} has no external effect")
        assert_true(resolve_capability(cap_id).resource_id is not None, f"{cap_id} maps to resource")
        assert_true(capability_to_tool_schema(cap_id) is not None, f"{cap_id} has schema")

    caps = select_capabilities_for_goal("what proof do we have")
    assert_true("eva.project_proof" in caps, "planner selects project proof")
    next_caps = select_capabilities_for_goal("what should we do next")
    assert_true("eva.project_next_step" in next_caps, "planner selects project next step")
    plan = create_task_plan("inspect this project")
    assert_true(any(step.capability_id == "eva.project_inspect" for step in plan.steps), "planner includes project inspection step")
    review = format_team_review("what proof do we have")
    assert_true("Project/reality route" in review, "team review includes project/reality route")
    assert_clean(review, "team review")

    control = format_control_center_text()
    assert_true("Project / Reality Check" in control, "control center includes project/reality section")
    assert_true("Current phase" in control and "Recommended next safe phase" in control, "control center includes phase and next step")
    assert_clean(control, "control center")

    source_files = [
        ROOT / "backend/eva/skills/project_inspection.py",
        ROOT / "backend/eva/skills/reality_check.py",
        ROOT / "backend/eva/core/natural_router.py",
    ]
    joined = "\n".join(path.read_text(encoding="utf-8") for path in source_files if path.exists()).lower()
    for forbidden in ["import playwright", "from playwright", "import pyautogui", "from pyautogui", "subprocess", "requests.", "httpx.", "pip install"]:
        assert_true(forbidden not in joined, f"no forbidden feature code: {forbidden}")

    print("verify_eva_project_reality_workflow: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
