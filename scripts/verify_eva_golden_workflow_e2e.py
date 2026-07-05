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


def assert_clean(text: str, label: str) -> None:
    forbidden = [
        "{'",
        "GoldenWorkflowResult(",
        "WorkSession(",
        "Traceback",
        "C:\\Users\\",
        ".env.local",
        "api_key",
        "Bearer ",
        "sk-",
        str(ROOT),
    ]
    for marker in forbidden:
        assert_true(marker not in text, f"{label} leaked unsafe/internal marker: {marker}")


def run_fast_command(message: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    result = maybe_handle_fast_command(message, ToolRegistry())
    assert_true(result is not None, f"command was not handled: {message}")
    return result[0]


def extract_approval_id(text: str) -> str:
    match = re.search(r"\b(fap_[A-Za-z0-9]+)\b", text)
    assert_true(match, "approval id missing from output")
    return match.group(1)


def main() -> int:
    created_paths: list[Path] = []
    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(temp_root / "approval_ledger.json")
        os.environ["EVA_FILE_AGENT_SANDBOX_ROOT"] = str(temp_root / "sandbox")
        os.environ["EVA_WORK_SESSIONS_DB_PATH"] = str(temp_root / "work_sessions.sqlite3")

        from backend.eva.agents.team_review import format_team_review
        from backend.eva.capabilities.permissions import get_capability_permission
        from backend.eva.capabilities.registry import get_capability
        from backend.eva.capabilities.resource_mapping import resolve_capability
        from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
        from backend.eva.control_center.status import format_control_center_text
        from backend.eva.core.natural_router import route_natural_request
        from backend.eva.file_agent.approval_ledger import approve_file_approval_request, get_file_approval_request
        from backend.eva.file_agent.real_apply import evaluate_real_apply_eligibility, verify_real_text_file_apply
        from backend.eva.golden_workflows.formatter import format_golden_workflow_status
        from backend.eva.golden_workflows.runner import get_golden_workflow_status
        from backend.eva.planner.capability_selector import select_capabilities_for_goal
        from backend.eva.planner.decomposer import create_task_plan
        from backend.eva.work_sessions.store import list_recent_work_sessions, list_session_events

        status = format_golden_workflow_status(get_golden_workflow_status())
        assert_true("Golden Workflows" in status and "safe_project_note_create" in status, "golden workflow status imports/formatting failed")
        assert_clean(status, "golden status")

        route = route_natural_request("create a project note about Phase 12L")
        assert_true(route.intent == "golden_project_note_create", "natural project note request did not select golden workflow")
        assert_true(route.authority_category == "golden_workflow", "project note authority category not golden workflow")

        start = run_fast_command("eva ask create a project note about Phase 12L")
        assert_clean(start, "start")
        assert_true("Eva ask" in start and "Work session:" in start, "eva ask did not create visible WorkSession")
        assert_true("Golden Workflow" in start and "approval request" in start.lower(), "natural request did not start golden workflow")
        assert_true("No real file was created" in start, "workflow real-created before approval")
        approval_id = extract_approval_id(start)

        approval = get_file_approval_request(approval_id)
        assert_true(approval is not None, "approval not recorded")
        target_path = ROOT / approval.display_path
        assert_true(approval.display_path.startswith(("docs/", "samples/")), "approval target not under safe folder")
        assert_true(approval.display_path.endswith((".md", ".txt")), "approval target is not text/markdown")
        assert_true(not target_path.exists(), "approval target unexpectedly exists before real create")

        no_approval_prompt = run_fast_command("eva ask apply the approved docs note for real")
        assert_clean(no_approval_prompt, "real create prompt before approval")
        assert_true("No approved FileAgent record" in no_approval_prompt or "No eligible narrow real-create approval" in no_approval_prompt, "unapproved real create did not stop safely")

        wrong = run_fast_command(f"eva file approval real create {approval_id} confirm real create wrong")
        assert_clean(wrong, "wrong confirmation")
        assert_true("blocked" in wrong.lower() or "Exact confirmation phrase required" in wrong, "wrong confirmation was not refused")
        assert_true(not target_path.exists(), "wrong confirmation created a file")

        approved = approve_file_approval_request(approval_id, approval.required_confirmation_phrase)
        assert_true(approved.status == "approved_for_future_apply", "approval could not be approved")

        sandbox = run_fast_command(f"eva file approval sandbox apply {approval_id}")
        assert_clean(sandbox, "sandbox apply")
        assert_true("Sandbox apply completed" in sandbox, "sandbox apply did not complete")
        assert_true("Real project files were not touched" in sandbox, "sandbox apply touched real files")

        eligibility = evaluate_real_apply_eligibility(approval_id)
        assert_true(eligibility.allowed, f"approval not eligible for narrow real create: {eligibility.reason}")
        exact_hint = run_fast_command("eva ask apply the approved docs note for real")
        assert_clean(exact_hint, "exact hint")
        assert_true(f"confirm real create {approval_id}" in exact_hint, "exact confirmation phrase not shown for eligible approval")

        exact = run_fast_command(f"eva ask confirm real create {approval_id}")
        assert_clean(exact, "exact create")
        assert_true("Real create completed" in exact and "Narrow real create-new-text-file" in exact, "exact confirmation did not use 12L real create")
        created_paths.append(target_path)
        assert_true(target_path.exists() and target_path.is_file(), "created file missing")
        assert_true(target_path.suffix in {".md", ".txt"}, "created file suffix unsafe")
        assert_true(target_path.parent.name in {"docs", "samples"}, "created file parent unsafe")

        verification = verify_real_text_file_apply(approval_id)
        assert_true(verification.verified and verification.confidence >= 0.9, "real-create verification did not pass")
        verify_output = run_fast_command(f"eva file approval real verify {approval_id}")
        assert_clean(verify_output, "verify output")
        assert_true("matches approved hash" in verify_output.lower() or "verified" in verify_output.lower(), "verification output missing hash evidence")

        second = run_fast_command(f"eva file approval real create {approval_id} confirm real create {approval_id}")
        assert_clean(second, "second create")
        assert_true("blocked" in second.lower() or "refused" in second.lower() or "Target already exists" in second, "existing target was not refused")

        latest_session = list_recent_work_sessions(limit=1)[0]
        timeline = run_fast_command(f"eva session timeline {latest_session.session_id}")
        assert_clean(timeline, "timeline")
        for expected in ["intent_routed", "skill_selected", "workflow_selected", "approval_selected", "real_create_seen", "verification_seen"]:
            assert_true(expected in timeline, f"timeline missing {expected}")

        control = format_control_center_text()
        assert_clean(control, "control")
        assert_true("Golden Workflows" in control and "Latest real-create status" in control, "control center missing golden workflow status")
        assert_true("Work Sessions / Audit Timeline" in control, "control center missing WorkSession status")

        proof = run_fast_command("eva workflow golden proof")
        assert_clean(proof, "proof")
        assert_true("Golden workflow proof" in proof and approval_id in proof, "golden proof missing latest approval evidence")
        assert_true("Rollback" in proof and "confirm rollback real create" in proof, "rollback option not visible in proof")

        rollback_hint = run_fast_command("eva ask rollback the golden workflow real create")
        assert_clean(rollback_hint, "rollback hint")
        assert_true("confirm rollback real create" in rollback_hint, "rollback did not require exact phrase")
        assert_true(target_path.exists(), "rollback hint deleted file without exact phrase")

        rollback_wrong = run_fast_command(f"eva file approval real rollback {approval_id} confirm rollback real create wrong")
        assert_clean(rollback_wrong, "wrong rollback")
        assert_true("Rollback refused" in rollback_wrong, "wrong rollback confirmation was not refused")
        assert_true(target_path.exists(), "wrong rollback deleted created file")

        rollback = run_fast_command(f"eva file approval real rollback {approval_id} confirm rollback real create {approval_id}")
        assert_clean(rollback, "rollback")
        assert_true("Rollback removed only the Eva-created file" in rollback, "exact rollback did not remove created file")
        assert_true(not target_path.exists(), "created file still exists after rollback")
        created_paths.clear()

        first = run_fast_command("eva ask create a project note about safety")
        second_start = run_fast_command("eva ask create a project note about demo")
        first_id = extract_approval_id(first)
        second_id = extract_approval_id(second_start)
        for request_id in (first_id, second_id):
            item = get_file_approval_request(request_id)
            assert_true(item is not None, "multi approval missing")
            approve_file_approval_request(request_id, item.required_confirmation_phrase)
        multi = run_fast_command("eva ask apply the approved docs note for real")
        assert_clean(multi, "multiple approval disambiguation")
        assert_true("Multiple eligible" in multi and "Specify" in multi, "multiple approvals were not disambiguated")

        broad = route_natural_request("edit an existing source file for real")
        assert_true(broad.refusal_reason or broad.authority_category in {"local_write", "unknown"}, "broad edit did not remain blocked/unknown")

        for capability_id in ("eva.golden_workflow_status", "eva.golden_workflow_test_plan", "eva.golden_workflow_proof"):
            assert_true(get_capability(capability_id) is not None, f"capability missing: {capability_id}")
            permission = get_capability_permission(capability_id)
            assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only metadata")
            assert_true(resolve_capability(capability_id).resource_id, f"resource mapping missing: {capability_id}")
            assert_true(capability_to_tool_schema(capability_id) is not None, f"tool schema missing: {capability_id}")

        caps = select_capabilities_for_goal("show golden workflow proof")
        assert_true("eva.golden_workflow_proof" in caps, "planner selector missed golden workflow proof")
        plan = create_task_plan("did the golden workflow pass")
        assert_true(any(step.capability_id == "eva.golden_workflow_proof" for step in plan.steps), "planner plan missing proof capability")
        review = format_team_review("show golden workflow proof")
        assert_clean(review, "team review")
        assert_true("golden workflow proof" in review.lower() or "Golden workflow" in review, "team review missing golden workflow proof")

        source_files = [
            ROOT / "backend/eva/golden_workflows/runner.py",
            ROOT / "backend/eva/golden_workflows/status.py",
            ROOT / "backend/eva/skills/workflows.py",
            ROOT / "backend/eva/skills/workflow_state.py",
        ]
        joined = "\n".join(path.read_text(encoding="utf-8") for path in source_files if path.exists()).lower()
        for forbidden in ["import playwright", "from playwright", "import pyautogui", "from pyautogui", "import subprocess", "subprocess.", "requests.", "httpx.", "pip install"]:
            assert_true(forbidden not in joined, f"forbidden execution code found: {forbidden}")

    for path in created_paths:
        if path.exists() and path.is_file():
            path.unlink()
    print("verify_eva_golden_workflow_e2e: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
