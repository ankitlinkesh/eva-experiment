from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_clean(text: str, label: str) -> None:
    forbidden = ["{'", "WorkflowStateSummary(", "WorkflowNextStep(", "WorkflowCandidate(", "LatestWorkflowContext(", "Traceback", "C:\\Users\\", ".env.local"]
    for token in forbidden:
        assert_true(token not in text, f"{label} leaked unsafe/internal token: {token}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="eva_12n_") as tmp:
        os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(Path(tmp) / "approvals.json")
        os.environ["EVA_FILE_AGENT_APPLY_SANDBOX_ROOT"] = str(Path(tmp) / "sandbox")

        from backend.eva.core.fast_commands import maybe_handle_fast_command
        from backend.eva.tools.registry import ToolRegistry
        from backend.eva.skills.workflow_state import (
            classify_next_fileagent_step,
            find_latest_approved_approval,
            find_latest_pending_approval,
            find_latest_real_create,
            find_latest_rollback_available,
            find_latest_sandbox_apply,
            format_latest_workflow_context,
            format_workflow_next_step,
            format_workflow_state_summary,
            summarize_fileagent_workflow_state,
        )
        from backend.eva.file_agent.approval_ledger import approve_file_approval_request, create_file_approval_request
        from backend.eva.file_agent.draft_preview import create_file_draft_preview
        from backend.eva.file_agent.real_apply import evaluate_real_apply_eligibility
        from backend.eva.capabilities.registry import build_default_registry
        from backend.eva.capabilities.permissions import get_capability_permission
        from backend.eva.capabilities.resource_mapping import resolve_capability
        from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
        from backend.eva.planner.capability_selector import select_capabilities_for_goal
        from backend.eva.planner.decomposer import create_task_plan
        from backend.eva.agents.team_review import format_team_review
        from backend.eva.control_center.status import format_control_center_text

        state = summarize_fileagent_workflow_state()
        assert_true(state.pending_approval_count == 0, "empty workflow state has zero pending approvals")
        assert_true(find_latest_pending_approval().status == "none", "empty latest pending lookup is friendly")
        assert_clean(format_workflow_state_summary(state), "empty workflow state")

        draft = create_file_draft_preview("docs/PHASE_12N_TEST_NOTE.md", "Phase 12N note\n")
        approval = create_file_approval_request(draft)
        pending = find_latest_pending_approval()
        assert_true(pending.status == "single", "one pending approval is detected")
        assert_true(pending.candidates[0].approval_id == approval.approval_id, "pending candidate id is preserved")

        second = create_file_approval_request(create_file_draft_preview("docs/PHASE_12N_SECOND_NOTE.md", "Second note\n"))
        multi = find_latest_pending_approval()
        assert_true(multi.status == "multiple", "multiple pending approvals are not guessed")
        assert_true("specify" in format_latest_workflow_context(multi).lower(), "multiple candidates ask for ID")

        approved = approve_file_approval_request(approval.approval_id, approval.required_confirmation_phrase)
        approved_context = find_latest_approved_approval()
        assert_true(approved_context.status == "single", "one approved approval is detected")
        eligibility = evaluate_real_apply_eligibility(approved.approval_id)
        assert_true(eligibility.allowed, "approved docs md note is eligible for 12L")

        assert_true(find_latest_sandbox_apply().status in {"none", "single", "multiple"}, "sandbox lookup is safe")
        assert_true(find_latest_real_create().status == "none", "missing real create is handled")
        assert_true(find_latest_rollback_available().status == "none", "missing rollback is handled")

        next_step = classify_next_fileagent_step("continue the project note workflow")
        assert_true(next_step.action in {"approve_pending", "disambiguate_pending_approval", "show_real_create_phrase", "show_sandbox_next", "start_project_note"}, "next step is classified")
        assert_clean(format_workflow_next_step(next_step), "workflow next step")

        tools = ToolRegistry()
        for command in [
            "eva workflow state",
            "eva workflow next",
            "eva workflow latest approval",
            "eva workflow latest sandbox",
            "eva workflow latest real create",
            "eva workflow latest rollback",
            "eva file latest status",
            "eva file latest real create",
            "eva file latest rollback",
        ]:
            result = maybe_handle_fast_command(command, tools)
            assert_true(result is not None, f"{command} handled")
            assert_clean(result[0], command)

        ask_continue = maybe_handle_fast_command("eva ask continue the project note workflow", tools)
        assert_true(ask_continue is not None, "continue workflow ask handled")
        assert_true("next step" in ask_continue[0].lower(), "continue workflow includes next-step framing")
        assert_clean(ask_continue[0], "ask continue")

        ask_real = maybe_handle_fast_command("eva ask apply the approved docs note for real", tools)
        assert_true(ask_real is not None, "real apply ask handled")
        assert_true("confirm real create" in ask_real[0], "real apply ask shows required exact phrase")
        assert_true("No file was created" in ask_real[0] or "Nothing was executed" in ask_real[0], "real apply ask does not execute without phrase")
        assert_clean(ask_real[0], "ask real apply")

        ask_verify = maybe_handle_fast_command("eva ask verify the latest real create", tools)
        assert_true(ask_verify is not None, "verify latest real create ask handled")
        assert_true("real create" in ask_verify[0].lower(), "verify latest real create is framed")
        assert_clean(ask_verify[0], "ask verify real create")

        ask_rollback = maybe_handle_fast_command("eva ask rollback the latest real create", tools)
        assert_true(ask_rollback is not None, "rollback latest real create ask handled")
        assert_true("confirm rollback real create" in ask_rollback[0] or "no rollback" in ask_rollback[0].lower(), "rollback ask requires exact phrase or explains absence")
        assert_clean(ask_rollback[0], "ask rollback real create")

        ask_done = maybe_handle_fast_command("eva ask are we actually done", tools)
        assert_true(ask_done is not None, "done/proof ask handled")
        assert_true("Evidence" in ask_done[0] or "proof" in ask_done[0].lower() or "verification" in ask_done[0].lower(), "done ask includes evidence framing")
        assert_clean(ask_done[0], "ask done")

        ask_next = maybe_handle_fast_command("eva ask what should I do next", tools)
        assert_true(ask_next is not None, "next ask handled")
        assert_true("Next step" in ask_next[0] or "safe next" in ask_next[0].lower(), "next ask gives safe next step")
        assert_clean(ask_next[0], "ask next")

        for blocked in [
            "eva ask edit the existing README for real",
            "eva ask update backend/eva/main.py for real",
            "eva ask apply all my changes for real",
        ]:
            result = maybe_handle_fast_command(blocked, tools)
            assert_true(result is not None, f"{blocked} handled")
            assert_true("blocked" in result[0].lower() or "refused" in result[0].lower(), f"{blocked} remains blocked")

        registry = build_default_registry()
        for cap_id in [
            "eva.workflow_state",
            "eva.workflow_next_step",
            "eva.workflow_latest_approval",
            "eva.workflow_latest_apply",
            "eva.workflow_disambiguate",
            "eva.file_latest_status",
        ]:
            assert_true(registry.get(cap_id) is not None, f"{cap_id} registered")
            permission = get_capability_permission(cap_id)
            assert_true(permission.read_only, f"{cap_id} is read-only/status")
            assert_true(not permission.external_effect, f"{cap_id} has no external effect")
            assert_true(resolve_capability(cap_id).resource_id is not None, f"{cap_id} maps to a resource")
            assert_true(capability_to_tool_schema(cap_id) is not None, f"{cap_id} schema exists")

        caps = select_capabilities_for_goal("continue the project note workflow")
        assert_true("eva.workflow_state" in caps and "eva.workflow_next_step" in caps, "planner selects workflow state/next")
        plan = create_task_plan("continue the project note workflow")
        assert_true(any(step.step_type in {"workflow_state", "workflow_next_step", "workflow_disambiguation"} for step in plan.steps), "planner includes workflow state/latest candidate steps")
        review = format_team_review("continue the project note workflow")
        assert_true("workflow state" in review.lower() or "latest" in review.lower(), "team review includes workflow evidence")
        assert_clean(review, "team review")

        control = format_control_center_text()
        assert_true("Latest Workflow State" in control, "control center includes workflow state section")
        assert_true("Locked Features" in control, "control center includes locked features")
        assert_clean(control, "control center")

        source_files = [
            Path("backend/eva/skills/workflow_state.py"),
            Path("backend/eva/core/natural_router.py"),
        ]
        joined = "\n".join(path.read_text(encoding="utf-8") for path in source_files if path.exists()).lower()
        assert_true("import playwright" not in joined and "from playwright" not in joined, "no Playwright imports added")
        assert_true("import pyautogui" not in joined and "from pyautogui" not in joined, "no PyAutoGUI imports added")
        assert_true("subprocess" not in joined, "no shell/subprocess feature code added")
        assert_true("requests." not in joined and "httpx." not in joined, "no cloud/network calls added")

    print("verify_eva_golden_workflow_ux: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
