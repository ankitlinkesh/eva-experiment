from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_clean_output(text: str, label: str) -> None:
    blocked = ["{'", "GoldenWorkflowRun(", "GoldenWorkflowResult(", "Traceback", ".env.local", str(ROOT)]
    for marker in blocked:
        assert_true(marker not in text, f"{label} leaked unsafe output marker: {marker}")


def run_fast_command(message: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    result = maybe_handle_fast_command(message, ToolRegistry())
    assert_true(result is not None, f"command was not handled: {message}")
    return result[0]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(Path(temp) / "approval_ledger.json")
        os.environ["EVA_FILE_AGENT_SANDBOX_ROOT"] = str(Path(temp) / "sandbox")

        from backend.eva.agents.team_review import format_team_review
        from backend.eva.capabilities.permissions import get_capability_permission
        from backend.eva.capabilities.registry import get_capability
        from backend.eva.capabilities.resource_mapping import resolve_capability
        from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
        from backend.eva.control_center.status import format_control_center_text
        from backend.eva.core.natural_router import route_natural_request
        from backend.eva.file_agent.approval_ledger import approve_file_approval_request, get_file_approval_request
        from backend.eva.golden_workflows import (
            continue_safe_project_note_workflow,
            format_golden_workflow_result,
            format_golden_workflow_status,
            get_golden_workflow_status,
            list_golden_workflows,
            start_safe_project_note_workflow,
        )
        from backend.eva.golden_workflows.project_note import build_project_note_draft, suggest_safe_target_path
        from backend.eva.planner.capability_selector import select_capabilities_for_goal
        from backend.eva.planner.decomposer import create_task_plan

        workflows = list_golden_workflows()
        assert_true(any(item.workflow_id == "safe_project_note_create" for item in workflows), "safe project note workflow missing")
        status_text = format_golden_workflow_status(get_golden_workflow_status())
        assert_true("Golden Workflows" in status_text and "safe_project_note_create" in status_text, "workflow status not human readable")
        assert_clean_output(status_text, "workflow status")

        draft = build_project_note_draft("create a project note about FileAgent")
        assert_true(draft.startswith("# "), "draft is not Markdown")
        assert_true("FileAgent" in draft and "Exact confirmation" in draft, "draft missing expected safety content")
        assert_true(not re.search(r"sk-[A-Za-z0-9]{12,}", draft), "draft contains secret-like value")

        target = suggest_safe_target_path("create a project note about FileAgent")
        assert_true(target.endswith((".md", ".txt")), "target extension is not safe")
        assert_true(target.startswith(("docs/", "samples/")), "target parent is not safe")
        assert_true(".." not in target and not Path(target).is_absolute(), "target traversal or absolute path")
        existing = ROOT / target
        existing.parent.mkdir(exist_ok=True)
        existing.write_text("existing", encoding="utf-8")
        try:
            alternative = suggest_safe_target_path("create a project note about FileAgent")
            assert_true(alternative != target and alternative.endswith(".md"), "existing target did not get numbered alternative")
        finally:
            existing.unlink(missing_ok=True)

        result = start_safe_project_note_workflow("Eva, create a project note about Eva")
        output = format_golden_workflow_result(result)
        assert_true(result.approval_id.startswith("fap_"), "workflow did not create approval")
        assert_true("approval request" in output.lower(), "workflow did not report approval request")
        assert_true("No real file was created" in output, "workflow appears to have real-created too early")
        assert_true("Next safe step" in output, "workflow did not show next step")
        assert_true("confirm real create" not in output.lower(), "real-create phrase appeared before eligibility")
        assert_clean_output(output, "start output")

        vague = continue_safe_project_note_workflow("yes")
        vague_output = format_golden_workflow_result(vague)
        assert_true(not vague.real_create_attempted, "vague confirmation attempted real create")
        assert_true("exact phrase" in vague_output.lower(), "vague confirmation did not explain exact phrase")

        approval = get_file_approval_request(result.approval_id)
        assert_true(approval is not None, "approval missing")
        approved = approve_file_approval_request(result.approval_id, approval.required_confirmation_phrase)
        assert_true(approved.status == "approved_for_future_apply", "approval could not be approved for future apply")

        sandbox = run_fast_command(f"eva file approval sandbox apply {result.approval_id}")
        assert_true("Sandbox apply completed" in sandbox and "Real project files were not touched" in sandbox, "sandbox apply not separate")

        eligibility = run_fast_command(f"eva ask create the approved file {result.approval_id}")
        assert_true("confirm real create" in eligibility and "No file was created" in eligibility, "eligibility did not show exact phrase safely")

        exact_preview = route_natural_request(f"confirm real create {result.approval_id}")
        assert_true(exact_preview.intent == "real_create_confirm", "exact confirmation did not route to real create gate")

        rollback_vague = continue_safe_project_note_workflow("rollback it")
        rollback_text = format_golden_workflow_result(rollback_vague)
        assert_true("confirm rollback real create" in rollback_text, "rollback did not require exact phrase")

        ask_note = run_fast_command("eva ask create a project note about Eva")
        assert_true("golden workflow" in ask_note.lower() and "approval" in ask_note.lower(), "eva ask note did not route to golden workflow")
        ask_fileagent = run_fast_command("eva ask make a safe markdown note about FileAgent")
        assert_true("safe_project_note_create" in ask_fileagent or "Golden Workflow" in ask_fileagent, "safe markdown note did not route to golden workflow")
        ask_status = run_fast_command("eva ask show golden workflow status")
        assert_true("Golden Workflows" in ask_status, "eva ask status did not route to workflow status")

        control = format_control_center_text()
        assert_true("Golden Workflows" in control, "control center missing golden workflows")
        assert_true("broad file writes disabled" in control.lower(), "control center lost broad-write warning")

        for capability_id in (
            "eva.golden_workflows_status",
            "eva.golden_workflow_project_note",
            "eva.golden_workflow_continue",
            "eva.golden_workflow_demo",
        ):
            assert_true(get_capability(capability_id) is not None, f"capability missing: {capability_id}")
            assert_true(resolve_capability(capability_id).resource_id, f"resource mapping missing: {capability_id}")
            assert_true(capability_to_tool_schema(capability_id) is not None, f"tool schema missing: {capability_id}")
        permission = get_capability_permission("eva.golden_workflow_project_note")
        assert_true(permission.reason and "broad" in permission.reason.lower(), "permission notes do not classify orchestration safely")

        selected = select_capabilities_for_goal("draft and safely create a note about this project")
        assert_true("eva.golden_workflow_project_note" in selected, "planner selector missed golden workflow")
        plan = create_task_plan("create a project note about Eva")
        assert_true(any(step.capability_id == "eva.golden_workflow_project_note" for step in plan.steps), "planner plan missing workflow capability")
        review = format_team_review("create a project note about Eva")
        assert_true("FileAgent" in review and "exact confirmation" in review.lower(), "team review missing FileAgent/exact confirmation")

        demo = run_fast_command("eva golden workflow demo")
        assert_true("safe_project_note_create" in demo and "No real file was created" in demo, "demo output unsafe or incomplete")
        for label, text in {
            "ask_note": ask_note,
            "ask_fileagent": ask_fileagent,
            "ask_status": ask_status,
            "control": control,
            "review": review,
            "demo": demo,
        }.items():
            assert_clean_output(text, label)

    print("verify_eva_golden_workflows: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
