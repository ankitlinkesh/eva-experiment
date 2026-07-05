from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} failed. {detail}")
    print({"case": name, "pass": True})


def assert_clean_output(name: str, output: str) -> None:
    forbidden = ["{'", "WriteEligibilityDecision(", "WriteSafetyPlan(", "RollbackPlan(", "VerificationPlan(", "Traceback", str(ROOT)]
    leaks = [item for item in forbidden if item and item in output]
    assert_true(name, not leaks, f"leaks={leaks}\n{output}")


def assert_no_secret_value(name: str, output: str) -> None:
    leaks = ["FAKE_VALUE", "FAKE_SECRET_VALUE", "sk-test-secret"]
    found = [item for item in leaks if item in output]
    assert_true(name, not found, f"found={found}\n{output}")


def main() -> None:
    module = importlib.import_module("backend.eva.file_agent.write_safety")
    assert_true("write_safety_module_imports", module is not None)

    from backend.eva.agents.file_agent import FileAgent
    from backend.eva.agents.team_review import format_team_review
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import build_default_registry
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.file_agent.draft_preview import (
        create_append_preview,
        create_file_draft_preview,
        create_text_replacement_preview,
    )
    from backend.eva.file_agent.status import format_file_agent_status
    from backend.eva.file_agent.write_safety import (
        build_rollback_plan,
        build_verification_plan,
        build_write_safety_plan,
        evaluate_write_eligibility,
        format_apply_readiness_report,
        format_rollback_plan,
        format_verification_plan,
        format_write_eligibility,
        format_write_policy,
        format_write_safety_plan,
    )
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan

    status = format_file_agent_status()
    assert_true("file_agent_status_mentions_apply_readiness", "apply-readiness" in status.lower() and "no real writes" in status.lower())

    target = ROOT / "docs" / "TEST_DRAFT_DO_NOT_CREATE.md"
    if target.exists():
        raise AssertionError("Verifier target unexpectedly exists before test.")

    safe_create = create_file_draft_preview("docs/TEST_DRAFT_DO_NOT_CREATE.md", "Hello draft")
    safe_append = create_append_preview("README.md", "Draft append text")
    safe_replace = create_text_replacement_preview("README.md", "Eva", "Eva Preview")

    create_report = format_apply_readiness_report(safe_create)
    append_report = format_apply_readiness_report(safe_append)
    replace_report = format_apply_readiness_report(safe_replace)
    assert_true("safe_create_apply_readiness_human", "Apply readiness" in create_report and "confirm apply file draft docs/TEST_DRAFT_DO_NOT_CREATE.md" in create_report)
    assert_true("safe_append_apply_readiness_human", "Apply readiness" in append_report and "backup" in append_report.lower())
    assert_true("safe_replace_requires_diff_backup_verification_confirmation", all(term in replace_report.lower() for term in ("diff review", "backup", "verification", "confirm apply file draft readme.md")))
    for name, output in {"create": create_report, "append": append_report, "replace": replace_report}.items():
        assert_true(f"{name}_report_says_no_mutation", "Planning only. No file was created, modified, backed up, or restored." in output)
        assert_clean_output(f"{name}_report_clean", output)
    assert_true("apply_readiness_did_not_create_file", not target.exists())

    env_preview = create_file_draft_preview(".env.local", "API_KEY=FAKE_VALUE")
    env_report = format_apply_readiness_report(env_preview)
    assert_true("env_apply_readiness_blocked", "blocked" in env_report.lower() or "not eligible" in env_report.lower())
    assert_no_secret_value("env_apply_readiness_redacted", env_report)

    runtime_preview = create_append_preview("backend/eva/data/test.txt", "hello")
    runtime_decision = evaluate_write_eligibility(runtime_preview)
    assert_true("runtime_apply_readiness_blocked", runtime_decision.blocked and not runtime_decision.eligible_for_future_apply)

    secret_preview = create_file_draft_preview("docs/TEST_DRAFT_DO_NOT_CREATE.md", "API_KEY=FAKE_SECRET_VALUE")
    secret_report = format_apply_readiness_report(secret_preview)
    assert_true("secret_like_content_blocks_future_apply", "secret-like" in secret_report.lower() and "not eligible" in secret_report.lower())
    assert_no_secret_value("secret_like_content_not_exposed", secret_report)

    eligibility = evaluate_write_eligibility(safe_replace)
    eligibility_output = format_write_eligibility(eligibility)
    assert_true("eligibility_requires_phrase", eligibility.requires_confirmation_phrase and eligibility.required_confirmation_phrase == "confirm apply file draft README.md")
    assert_clean_output("eligibility_output_clean", eligibility_output)

    safety_plan = build_write_safety_plan(safe_replace)
    safety_output = format_write_safety_plan(safety_plan)
    assert_true("write_safety_plan_human", "backup" in safety_output.lower() and "diff review" in safety_output.lower())
    assert_clean_output("write_safety_plan_clean", safety_output)

    rollback_output = format_rollback_plan(build_rollback_plan(safe_replace))
    assert_true("rollback_plan_human", "rollback plan" in rollback_output.lower() and "no backup" in rollback_output.lower())
    assert_clean_output("rollback_plan_clean", rollback_output)

    verification_output = format_verification_plan(build_verification_plan(safe_replace))
    assert_true("verification_plan_human", "verification plan" in verification_output.lower() and "read back" in verification_output.lower())
    assert_clean_output("verification_plan_clean", verification_output)

    policy_output = format_write_policy("README.md")
    assert_true("write_policy_human", "FileAgent apply policy" in policy_output and "cannot apply writes yet" in policy_output)
    assert_clean_output("write_policy_clean", policy_output)

    commands = {
        "cmd_apply_policy": "eva file apply policy",
        "cmd_readiness_create": "eva file apply readiness create docs/TEST_DRAFT.md text Hello draft",
        "cmd_readiness_append": "eva file apply readiness append README.md text Draft append text",
        "cmd_readiness_replace": "eva file apply readiness replace README.md old Eva new Eva Preview",
        "cmd_write_safety": "eva file write safety README.md",
        "cmd_rollback_plan": "eva file rollback plan README.md",
        "cmd_env_blocked": "eva file apply readiness create .env.local text API_KEY=FAKE_VALUE",
    }
    for name, command in commands.items():
        handled = maybe_handle_fast_command(command, tools=None, memory=None)
        assert_true(name, handled is not None, command)
        output = handled[0]
        assert_true(f"{name}_planning_only", "Planning only. No file was created, modified, backed up, or restored." in output or "cannot apply writes yet" in output)
        assert_clean_output(f"{name}_clean", output)
        assert_no_secret_value(f"{name}_no_secret", output)

    confirm_attempt = maybe_handle_fast_command("confirm apply file draft README.md", tools=None, memory=None)
    assert_true("confirmation_phrase_not_execution", confirm_attempt is None or "created" not in str(confirm_attempt[0]).lower())

    execute = FileAgent().execute({"capability_id": "file.apply_write", "input_summary": "write README"})
    assert_true("file_agent_execute_still_refuses_real_writes", execute.status == "refused" and "refused" in execute.summary.lower())

    selected = select_capabilities_for_goal("update README safely")
    assert_true("planner_update_readme_selects_apply_readiness", "file.apply_readiness" in selected, str(selected))
    plan = create_task_plan("update README safely")
    joined = "\n".join(f"{step.title} {step.notes} {step.permission_status} {step.availability_status}" for step in plan.steps)
    assert_true("planner_marks_future_apply_not_enabled", "Future apply" in joined or "preview" in joined.lower())

    review = format_team_review("apply this file change")
    assert_true("team_review_routes_apply_to_fileagent", "FileAgent" in review and "preview" in review.lower())

    registry = build_default_registry()
    for capability_id in ("file.apply_readiness", "file.write_safety_policy", "file.rollback_plan", "file.verification_plan"):
        cap = registry.get(capability_id)
        permission = get_capability_permission(capability_id)
        resolution = resolve_capability(capability_id)
        schema = capability_to_tool_schema(capability_id)
        assert_true(f"{capability_id}_registered", cap is not None)
        assert_true(f"{capability_id}_permission_readonly_preview", permission.read_only and not permission.writes_local_data)
        assert_true(f"{capability_id}_resource_mapping", resolution.resource_id == "eva-file-agent-v1" and resolution.preview_only)
        assert_true(f"{capability_id}_schema_exists", schema is not None)

    for module_name in ("backend.eva.file_agent.write_safety",):
        source = (ROOT / module_name.replace(".", "/")).with_suffix(".py").read_text(encoding="utf-8")
        forbidden = ["subprocess", "playwright", "pyautogui", "mcp"]
        found = [item for item in forbidden if item in source.lower()]
        assert_true(f"{module_name}_forbidden_imports_absent", not found, str(found))

    for script_name in (
        "verify_eva_file_agent_draft_preview.py",
        "verify_eva_file_agent_understanding.py",
        "verify_eva_file_agent_readonly.py",
        "verify_eva_agent_framework_quality.py",
        "verify_eva_planner_v3_quality.py",
        "verify_eva_capability_resource_mapping.py",
        "verify_eva_stabilization_v1.py",
    ):
        assert_true(f"existing_verifier_present_{script_name}", (ROOT / "scripts" / script_name).exists())

    assert_true("no_file_created_or_modified_by_verifier", not target.exists())
    print({"overall_pass": True, "failures": 0})


if __name__ == "__main__":
    main()
