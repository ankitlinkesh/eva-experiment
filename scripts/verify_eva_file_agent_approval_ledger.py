from __future__ import annotations

import importlib
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SECRET_VALUE = "FAKE_VALUE"


def assert_true(name: str, condition: bool, detail: str = "") -> None:
    if not condition:
        raise AssertionError(f"{name} failed. {detail}")
    print({"case": name, "pass": True})


def assert_clean_output(name: str, output: str) -> None:
    forbidden = [
        "{'",
        "FileApprovalRequest(",
        "FileApprovalEvent(",
        "FileApprovalLedgerStatus(",
        "FileAuthorityDecision(",
        "Traceback",
        str(ROOT),
        "C:\\Users\\",
        "C:/Users/",
        SECRET_VALUE,
        "sk-test-secret",
    ]
    found = [item for item in forbidden if item and item in str(output)]
    assert_true(name, not found, f"found={found}\n{output}")


def _set_test_ledger_env() -> tempfile.TemporaryDirectory[str]:
    tempdir = tempfile.TemporaryDirectory()
    os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(Path(tempdir.name) / "approval_ledger.json")
    return tempdir


def main() -> None:
    tempdir = _set_test_ledger_env()
    try:
        ledger_module = importlib.import_module("backend.eva.file_agent.approval_ledger")
        authority_module = importlib.import_module("backend.eva.file_agent.authority")
        assert_true("approval_ledger_module_imports", ledger_module is not None)
        assert_true("authority_module_imports", authority_module is not None)

        from backend.eva.agents.file_agent import FileAgent
        from backend.eva.agents.team_review import format_team_review
        from backend.eva.capabilities.permissions import get_capability_permission
        from backend.eva.capabilities.registry import build_default_registry
        from backend.eva.capabilities.resource_mapping import resolve_capability
        from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
        from backend.eva.core.fast_commands import maybe_handle_fast_command
        from backend.eva.file_agent.approval_ledger import (
            approve_file_approval_request,
            cancel_file_approval_request,
            create_file_approval_request,
            deny_file_approval_request,
            expire_old_file_approvals,
            format_file_approval_events,
            format_file_approval_ledger_status,
            format_file_approval_list,
            format_file_approval_request,
            get_file_approval_request,
            list_file_approval_requests,
        )
        from backend.eva.file_agent.authority import evaluate_file_authority_for_approval, format_file_authority_decision
        from backend.eva.file_agent.draft_preview import create_append_preview, create_file_draft_preview, create_text_replacement_preview
        from backend.eva.file_agent.status import format_file_agent_status
        from backend.eva.planner.capability_selector import select_capabilities_for_goal
        from backend.eva.planner.decomposer import create_task_plan

        target = ROOT / "docs" / "TEST_APPROVAL_DO_NOT_CREATE.md"
        if target.exists():
            raise AssertionError("Verifier target unexpectedly exists before test.")

        status = format_file_agent_status()
        assert_true("file_agent_status_mentions_approval_ledger", "approval ledger" in status.lower() and "no real writes" in status.lower())
        assert_clean_output("file_agent_status_clean", status)

        ledger_status = format_file_approval_ledger_status()
        assert_true("approval_status_human_readable", "approval ledger" in ledger_status.lower())
        assert_clean_output("approval_status_clean", ledger_status)

        safe_create = create_file_draft_preview("docs/TEST_APPROVAL_DO_NOT_CREATE.md", "Hello draft")
        safe_append = create_append_preview("README.md", "Draft append text")
        safe_replace = create_text_replacement_preview("README.md", "Eva", "Eva Preview")

        authority = evaluate_file_authority_for_approval(safe_create)
        authority_output = format_file_authority_decision(authority)
        assert_true("authority_allows_safe_preview_but_not_apply", authority.approval_request_allowed and not authority.actual_apply_allowed)
        assert_clean_output("authority_output_clean", authority_output)

        create_req = create_file_approval_request(safe_create)
        append_req = create_file_approval_request(safe_append)
        replace_req = create_file_approval_request(safe_replace)
        for label, request in {"create": create_req, "append": append_req, "replace": replace_req}.items():
            assert_true(f"safe_{label}_approval_metadata_only", request.status == "pending" and request.future_apply_enabled is False)
            output = format_file_approval_request(request)
            assert_true(f"safe_{label}_approval_output_has_id_phrase", request.approval_id in output and request.required_confirmation_phrase in output)
            assert_true(f"safe_{label}_approval_no_write_message", "No file was created, modified, backed up, restored, or applied." in output)
            assert_clean_output(f"safe_{label}_approval_output_clean", output)

        assert_true("approval_did_not_create_file", not target.exists())

        wrong = approve_file_approval_request(create_req.approval_id, "wrong phrase")
        assert_true("approve_wrong_phrase_refuses", wrong.status == "pending")
        exact = approve_file_approval_request(create_req.approval_id, create_req.required_confirmation_phrase)
        exact_output = format_file_approval_request(exact)
        assert_true("approve_exact_phrase_future_only", exact.status == "approved_for_future_apply" and not exact.future_apply_enabled)
        assert_true("approved_output_says_no_write", "Approval recorded for future apply only. No file was created or modified." in exact_output)
        assert_clean_output("approved_output_clean", exact_output)

        denied = deny_file_approval_request(append_req.approval_id, "test denial")
        cancelled = cancel_file_approval_request(replace_req.approval_id, "test cancel")
        assert_true("deny_marks_denied", denied.status == "denied")
        assert_true("cancel_marks_cancelled", cancelled.status == "cancelled")
        events_output = format_file_approval_events(denied.approval_id)
        assert_true("events_human_readable", "Approval events" in events_output and "denied" in events_output.lower())
        assert_clean_output("events_output_clean", events_output)

        expired_count = expire_old_file_approvals(max_age_minutes=0)
        assert_true("expire_handles_old_or_none", isinstance(expired_count, int) and expired_count >= 0)

        pending_output = format_file_approval_list(list_file_approval_requests(status="pending"))
        assert_true("pending_list_human_readable", "File approval requests" in pending_output)
        assert_clean_output("pending_list_clean", pending_output)

        env_preview = create_file_draft_preview(".env.local", f"API_KEY={SECRET_VALUE}")
        env_req = create_file_approval_request(env_preview)
        env_output = format_file_approval_request(env_req)
        assert_true("env_local_approval_blocked", env_req.status == "blocked")
        assert_clean_output("env_local_approval_output_clean", env_output)

        runtime_preview = create_append_preview("backend/eva/data/test.txt", "hello")
        runtime_req = create_file_approval_request(runtime_preview)
        assert_true("runtime_approval_blocked", runtime_req.status == "blocked")

        secret_preview = create_file_draft_preview("docs/TEST_APPROVAL_DO_NOT_CREATE.md", f"API_KEY={SECRET_VALUE}")
        secret_req = create_file_approval_request(secret_preview)
        secret_output = format_file_approval_request(secret_req)
        assert_true("secret_like_content_blocks_approval", secret_req.status == "blocked")
        assert_clean_output("secret_approval_output_clean", secret_output)

        ledger_text = Path(os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"]).read_text(encoding="utf-8")
        assert_true("approval_ledger_does_not_store_raw_secret", SECRET_VALUE not in ledger_text and "API_KEY=" not in ledger_text)

        commands = {
            "cmd_status": "eva file approval status",
            "cmd_request_create": "eva file approval request create docs/TEST_DRAFT.md text Hello draft",
            "cmd_request_append": "eva file approval request append README.md text Draft append text",
            "cmd_request_replace": "eva file approval request replace README.md old Eva new Eva Preview",
            "cmd_pending": "eva file approvals pending",
            "cmd_env_blocked": f"eva file approval request create .env.local text API_KEY={SECRET_VALUE}",
        }
        command_outputs: dict[str, str] = {}
        for name, command in commands.items():
            handled = maybe_handle_fast_command(command, tools=None, memory=None)
            assert_true(name, handled is not None, command)
            command_outputs[name] = handled[0]
            assert_clean_output(f"{name}_clean", handled[0])

        request_ids = [item.approval_id for item in list_file_approval_requests(status="pending", limit=10)]
        assert_true("fast_commands_created_pending_approvals", bool(request_ids))
        sample_id = request_ids[0]
        for name, command in {
            "cmd_view": f"eva file approval {sample_id}",
            "cmd_wrong_approve": f"eva file approval approve {sample_id} confirm wrong phrase",
            "cmd_deny": f"eva file approval deny {sample_id}",
            "cmd_events": f"eva file approval events {sample_id}",
            "cmd_cancel": f"eva file approval cancel {sample_id}",
            "cmd_expire": "eva file approvals expire",
        }.items():
            handled = maybe_handle_fast_command(command, tools=None, memory=None)
            assert_true(name, handled is not None, command)
            assert_clean_output(f"{name}_clean", handled[0])

        execute = FileAgent().execute({"capability_id": "file.apply_write", "input_summary": "write README"})
        assert_true("file_agent_execute_still_refuses_real_writes", execute.status == "refused" and "refused" in execute.summary.lower())

        selected = select_capabilities_for_goal("approve this file change")
        assert_true("planner_selects_approval_capability", "file.approval_request_create" in selected or "file.approval_approve_future" in selected, str(selected))
        plan = create_task_plan("apply approved file change")
        joined = "\n".join(f"{step.title} {step.notes} {step.permission_status} {step.availability_status}" for step in plan.steps)
        assert_true("planner_marks_future_apply_unavailable", "future apply" in joined.lower() and "preview" in joined.lower())
        review = format_team_review("create an approval for this README edit")
        assert_true("team_review_routes_approval_to_fileagent", "FileAgent" in review and ("metadata" in review.lower() or "preview" in review.lower()))

        registry = build_default_registry()
        approval_caps = (
            "file.approval_status",
            "file.approval_request_create",
            "file.approval_list_pending",
            "file.approval_view",
            "file.approval_approve_future",
            "file.approval_deny",
            "file.approval_cancel",
            "file.approval_events",
            "file.approval_expire",
        )
        for capability_id in approval_caps:
            cap = registry.get(capability_id)
            permission = get_capability_permission(capability_id)
            resolution = resolve_capability(capability_id)
            schema = capability_to_tool_schema(capability_id)
            assert_true(f"{capability_id}_registered", cap is not None)
            assert_true(f"{capability_id}_resource_mapping", resolution.resource_id == "eva-file-agent-v1")
            assert_true(f"{capability_id}_schema_exists", schema is not None)
            if capability_id == "file.approval_approve_future":
                assert_true("approval_approve_permission_confirmation", permission.writes_local_data and permission.requires_confirmation and not permission.read_only)

        for module_name in ("backend.eva.file_agent.approval_ledger", "backend.eva.file_agent.authority"):
            source = (ROOT / module_name.replace(".", "/")).with_suffix(".py").read_text(encoding="utf-8")
            lowered = source.lower()
            forbidden = ["subprocess", "playwright", "pyautogui", "mcp", ".env.local"]
            found = [item for item in forbidden if item in lowered]
            assert_true(f"{module_name}_forbidden_imports_absent", not found, str(found))

        for script_name in (
            "verify_eva_file_agent_write_safety.py",
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
    finally:
        tempdir.cleanup()
        os.environ.pop("EVA_FILE_AGENT_APPROVAL_LEDGER_PATH", None)


if __name__ == "__main__":
    main()
