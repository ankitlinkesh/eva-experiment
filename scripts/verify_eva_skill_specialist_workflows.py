from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_clean_output(text: str, label: str) -> None:
    forbidden = ["{'", "SpecialistRole(", "EvaSkill(", "EvaWorkflow(", "SkillStep(", "Traceback", "C:\\Users\\", ".env.local"]
    for token in forbidden:
        assert_true(token not in text, f"{label} leaked unsafe/internal output token: {token}")


def main() -> int:
    from backend.eva.specialists.registry import get_specialist, list_specialists
    from backend.eva.specialists.selector import select_specialists_for_request
    from backend.eva.specialists.status import format_specialist_status
    from backend.eva.skills.registry import get_skill, get_workflow, list_skills, list_workflows
    from backend.eva.skills.selector import select_skills_for_request, select_workflow_for_request
    from backend.eva.skills.status import format_skill_status, format_workflow_status
    from backend.eva.skills.workflows import (
        build_fileagent_project_note_workflow,
        explain_next_workflow_step,
        format_fileagent_project_note_workflow,
    )
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry
    from backend.eva.capabilities.registry import build_default_registry
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review
    from backend.eva.control_center.status import format_control_center_text

    specialists = list_specialists()
    specialist_ids = {item.id for item in specialists}
    expected_specialists = {
        "fileagent_workflow_specialist",
        "codebase_onboarding_specialist",
        "technical_writer",
        "reality_checker",
        "evidence_collector",
        "test_results_analyzer",
        "safety_reviewer",
    }
    assert_true(expected_specialists.issubset(specialist_ids), "all Phase 12M specialist roles are registered")
    assert_true(len(specialist_ids) == len(specialists), "specialist ids are unique")
    assert_true(get_specialist("technical_writer") is not None, "specialist lookup works")
    assert_true("technical_writer" in [item.id for item in select_specialists_for_request("draft a README section but do not apply it")], "technical writer selected for draft")
    assert_true("reality_checker" in [item.id for item in select_specialists_for_request("are we actually done and what proof do we have")], "reality checker selected for proof")

    skills = list_skills()
    skill_ids = {item.id for item in skills}
    expected_skills = {
        "fileagent_create_project_note",
        "fileagent_safe_draft",
        "project_inspection_readonly",
        "verification_before_completion",
        "safety_status_review",
    }
    assert_true(expected_skills.issubset(skill_ids), "all Phase 12M skills are registered")
    assert_true(get_skill("fileagent_safe_draft") is not None, "skill lookup works")
    assert_true("fileagent_safe_draft" in [item.id for item in select_skills_for_request("draft a README section but do not apply it")], "safe draft skill selected")
    assert_true("verification_before_completion" in [item.id for item in select_skills_for_request("are we actually done")], "verification skill selected")

    workflows = list_workflows()
    workflow_ids = {item.id for item in workflows}
    assert_true("fileagent_project_note_create" in workflow_ids, "project note workflow registered")
    assert_true(get_workflow("fileagent_project_note_create") is not None, "workflow lookup works")
    assert_true(select_workflow_for_request("make a safe project note about phase 12m").id == "fileagent_project_note_create", "project note workflow selected")

    workflow = build_fileagent_project_note_workflow("make a docs note about phase 12m", target_hint="docs/PHASE_12M_NOTE.md", content_hint="Phase 12M summary")
    assert_true(workflow.id == "fileagent_project_note_create", "workflow builder returns project note workflow")
    assert_true(workflow.mode == "workflow_plan_only", "workflow is plan-only")
    assert_true(workflow.real_execution_scope == "phase12l_create_new_text_file_only", "workflow names narrow real scope")
    assert_true(any(step.requires_confirmation for step in workflow.steps), "workflow includes confirmation step")
    assert_true(any(step.verification_required for step in workflow.steps), "workflow includes verification step")
    assert_true(any(step.rollback_available for step in workflow.steps), "workflow includes rollback-aware step")
    formatted_workflow = format_fileagent_project_note_workflow(workflow)
    assert_true("No file was created" in formatted_workflow, "workflow formatter states no execution")
    assert_true("create-new-text-file only" in formatted_workflow, "workflow formatter states narrow gate")
    assert_true("docs/PHASE_12M_NOTE.md" in formatted_workflow, "workflow includes safe relative target hint")
    assert_clean_output(formatted_workflow, "workflow formatter")
    assert_true("Next step" in explain_next_workflow_step(workflow), "next step explanation exists")

    for command in [
        "eva specialists status",
        "eva specialists list",
        "eva specialist technical_writer",
        "eva skills status",
        "eva skills list",
        "eva skill fileagent_safe_draft",
        "eva workflows status",
        "eva workflows list",
        "eva workflow fileagent_project_note_create",
    ]:
        result = maybe_handle_fast_command(command, ToolRegistry())
        assert_true(result is not None, f"{command} is handled")
        assert_clean_output(result[0], command)

    ask_project_note = maybe_handle_fast_command("eva ask make a docs note about the latest FileAgent phase", ToolRegistry())
    assert_true(ask_project_note is not None, "eva ask project note is handled")
    assert_true("Specialist route" in ask_project_note[0], "eva ask includes specialist route")
    assert_true("Skill route" in ask_project_note[0], "eva ask includes skill route")
    assert_true("Workflow route" in ask_project_note[0], "eva ask includes workflow route")
    assert_true("No file was created" in ask_project_note[0], "eva ask project note stays plan/safe workflow")
    assert_clean_output(ask_project_note[0], "eva ask project note")

    ask_done = maybe_handle_fast_command("eva ask are we actually done and what proof do we have", ToolRegistry())
    assert_true(ask_done is not None, "eva ask proof is handled")
    assert_true("verification_before_completion" in ask_done[0], "eva ask proof includes verification skill")
    assert_clean_output(ask_done[0], "eva ask proof")

    ask_real_actions = maybe_handle_fast_command("eva ask what real actions can Eva do now", ToolRegistry())
    assert_true(ask_real_actions is not None, "eva ask real actions is handled")
    assert_true("create-new-text-file only" in ask_real_actions[0], "real action answer remains narrow")
    assert_clean_output(ask_real_actions[0], "eva ask real actions")

    route = route_natural_request("make a docs note about phase 12m")
    assert_true(route.intent == "golden_project_note_create", "natural router recognizes docs note workflow")
    route = route_natural_request("are we actually done and what proof do we have")
    assert_true(route.intent in {"project_proof", "done_check"}, "natural router recognizes proof workflow")

    registry = build_default_registry()
    for cap_id in [
        "eva.specialists_status",
        "eva.specialist_select",
        "eva.skills_status",
        "eva.skill_select",
        "eva.workflow_select",
        "eva.workflow_plan",
        "eva.fileagent_project_note_workflow",
    ]:
        cap = registry.get(cap_id)
        assert_true(cap is not None, f"{cap_id} capability registered")
        permission = get_capability_permission(cap_id)
        assert_true(permission.external_effect is False, f"{cap_id} has no external effect")
        assert_true(resolve_capability(cap_id).resource_id is not None, f"{cap_id} maps to a resource")
        assert_true(capability_to_tool_schema(cap_id) is not None, f"{cap_id} has schema preview")

    project_note_caps = select_capabilities_for_goal("make a docs note about phase 12m")
    assert_true("eva.fileagent_project_note_workflow" in project_note_caps, "planner selects project note workflow capability")
    draft_caps = select_capabilities_for_goal("draft a README section but do not apply it")
    assert_true("eva.skill_select" in draft_caps, "planner selects skill capability for draft")
    proof_caps = select_capabilities_for_goal("are we actually done and what proof do we have")
    assert_true("eva.workflow_plan" in proof_caps or "eva.skill_select" in proof_caps, "planner selects workflow/skill for proof")

    plan = create_task_plan("make a docs note about phase 12m")
    assert_true(any(step.step_type in {"workflow_plan", "specialist_selection", "skill_selection"} for step in plan.steps), "plan includes specialist/skill/workflow steps")
    review = format_team_review("make a docs note about phase 12m")
    assert_true("Specialist workflow route" in review or "Workflow" in review, "team review mentions workflow/specialist route")
    assert_clean_output(review, "team review")

    status_text = "\n\n".join([format_specialist_status(), format_skill_status(), format_workflow_status(), format_control_center_text()])
    assert_true("Specialists" in status_text and "Skills" in status_text and "Workflows" in status_text, "status surfaces include specialists, skills, workflows")
    assert_clean_output(status_text, "status surfaces")

    assert_true("mcp" not in formatted_workflow.lower() or "no mcp" in formatted_workflow.lower(), "workflow does not enable MCP")
    assert_true("pyautogui" not in formatted_workflow.lower(), "workflow does not enable PyAutoGUI")
    assert_true("playwright" not in formatted_workflow.lower(), "workflow does not enable Playwright")

    print("verify_eva_skill_specialist_workflows: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
