from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def emit(case: str, passed: bool, **payload: Any) -> int:
    ok = bool(passed)
    print(json.dumps({"case": case, "pass": ok, **payload}, indent=2, ensure_ascii=False))
    return 0 if ok else 1


def clean_output(text: str) -> bool:
    blocked = (
        "{'",
        "FileApplyRequest(",
        "FileApplyResult(",
        "FileBackupRecord(",
        "FileVerificationResult(",
        "FileRollbackResult(",
        "Traceback",
        "C:\\Users\\",
        "C:/Users/",
        "sqlite3.Row",
        "sk-test-secret",
    )
    return bool(text and not any(marker in text for marker in blocked))


def run_nested(script_name: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=int(os.environ.get("EVA_VERIFY_NESTED_TIMEOUT_SECONDS", "1200")),
    )
    return result.returncode == 0, result.stdout[-1600:]


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory(prefix="eva_file_apply_") as temp_dir:
        temp = Path(temp_dir)
        os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(temp / "approval_ledger.json")
        os.environ["EVA_FILE_AGENT_APPLY_SANDBOX_ROOT"] = str(temp / "apply_sandbox")

        try:
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
            )
            from backend.eva.file_agent.apply_executor import (
                apply_draft_to_sandbox,
                build_apply_request_from_approval,
                create_sandbox_apply_workspace,
                evaluate_apply_request,
                format_apply_executor_status,
                format_apply_request,
                format_apply_result,
                format_rollback_result,
                format_verification_result,
                is_sandbox_path,
                rollback_sandbox_apply,
                verify_sandbox_apply,
            )
            from backend.eva.file_agent.draft_preview import create_file_draft_preview
            from backend.eva.file_agent.status import format_file_agent_status
            from backend.eva.planner.decomposer import create_task_plan
            from backend.eva.tools.registry import ToolRegistry
        except Exception as exc:
            failures += emit("apply_executor_module_imports", False, error=str(exc))
            print(json.dumps({"overall_pass": False, "failures": failures}, indent=2))
            return 1

        failures += emit("apply_executor_module_imports", True)

        status_text = format_file_agent_status()
        executor_status = format_apply_executor_status()
        failures += emit(
            "file_agent_status_mentions_sandbox_apply",
            "sandbox apply" in status_text.lower() and "real apply" in status_text.lower() and clean_output(status_text),
            output=status_text,
        )
        failures += emit(
            "executor_status_human_readable",
            "Sandbox only" in executor_status and "No real project file" in executor_status and clean_output(executor_status),
            output=executor_status,
        )

        workspace = create_sandbox_apply_workspace()
        failures += emit("sandbox_workspace_is_runtime_sandbox", is_sandbox_path(workspace))

        real_target = ROOT / "docs" / "TEST_DRAFT.md"
        if real_target.exists():
            failures += emit("test_target_absent_before_run", False, note="docs/TEST_DRAFT.md exists; verifier requires an unused target")
        else:
            failures += emit("test_target_absent_before_run", True)

        safe_preview = create_file_draft_preview("docs/TEST_DRAFT.md", "Hello sandbox")
        safe_approval = create_file_approval_request(safe_preview)
        approved = approve_file_approval_request(safe_approval.approval_id, safe_approval.required_confirmation_phrase)
        request = build_apply_request_from_approval(approved.approval_id)
        decision = evaluate_apply_request(request)
        failures += emit(
            "safe_approval_can_build_sandbox_apply_request",
            request.allowed and request.sandbox_only and decision.sandbox_apply_allowed and not decision.real_apply_allowed,
            request=format_apply_request(request),
        )

        result = apply_draft_to_sandbox(request)
        result_text = format_apply_result(result)
        failures += emit(
            "sandbox_apply_writes_only_under_sandbox",
            result.ok and result.sandbox_only and is_sandbox_path(result.sandbox_target) and Path(result.sandbox_target).exists(),
            output=result_text,
        )
        failures += emit(
            "sandbox_apply_does_not_modify_real_target",
            not real_target.exists() and "No real project file was created, modified, backed up, restored, or applied." in result_text,
            output=result_text,
        )
        failures += emit(
            "sandbox_backup_is_sandbox_only",
            result.backup is not None and is_sandbox_path(result.backup.backup_path),
            backup=result.backup.as_dict() if result.backup else None,
        )
        verification = verify_sandbox_apply(request, result)
        verification_text = format_verification_result(verification)
        failures += emit(
            "sandbox_verification_passes_after_apply",
            verification.verified and verification.confidence >= 0.9 and clean_output(verification_text),
            output=verification_text,
        )
        rollback = rollback_sandbox_apply(result)
        rollback_text = format_rollback_result(rollback)
        failures += emit(
            "sandbox_rollback_restores_sandbox_state_only",
            rollback.attempted and rollback.success and is_sandbox_path(rollback.restored_path or "") and not real_target.exists() and clean_output(rollback_text),
            output=rollback_text,
        )

        pending = create_file_approval_request(create_file_draft_preview("docs/PENDING_ONLY.md", "pending only"))
        pending_request = build_apply_request_from_approval(pending.approval_id)
        failures += emit("pending_approval_refused", not pending_request.allowed and "approved_for_future_apply" in pending_request.reason)

        denied = create_file_approval_request(create_file_draft_preview("docs/DENIED_ONLY.md", "denied only"))
        deny_file_approval_request(denied.approval_id)
        denied_request = build_apply_request_from_approval(denied.approval_id)
        failures += emit("denied_approval_refused", not denied_request.allowed and "denied" in denied_request.reason)

        cancelled = create_file_approval_request(create_file_draft_preview("docs/CANCELLED_ONLY.md", "cancelled only"))
        cancel_file_approval_request(cancelled.approval_id)
        cancelled_request = build_apply_request_from_approval(cancelled.approval_id)
        failures += emit("cancelled_approval_refused", not cancelled_request.allowed and "cancelled" in cancelled_request.reason)

        expired = create_file_approval_request(create_file_draft_preview("docs/EXPIRED_ONLY.md", "expired only"))
        expire_old_file_approvals(max_age_minutes=0)
        expired_request = build_apply_request_from_approval(expired.approval_id)
        failures += emit("expired_approval_refused", not expired_request.allowed and "expired" in expired_request.reason)

        missing_request = build_apply_request_from_approval("fap_missing")
        failures += emit("nonexistent_approval_refused", not missing_request.allowed and "not found" in missing_request.reason.lower())

        env_preview = create_file_draft_preview(".env.local", "x")
        env_approval = create_file_approval_request(env_preview)
        env_request = build_apply_request_from_approval(env_approval.approval_id)
        failures += emit("env_local_approval_not_applied", env_approval.status == "blocked" and not env_request.allowed)

        runtime_preview = create_file_draft_preview("backend/eva/data/blocked.txt", "runtime")
        runtime_approval = create_file_approval_request(runtime_preview)
        runtime_request = build_apply_request_from_approval(runtime_approval.approval_id)
        failures += emit("runtime_target_approval_not_applied", runtime_approval.status == "blocked" and not runtime_request.allowed)

        secret_preview = create_file_draft_preview("docs/SECRET_DRAFT.md", "sk-test-secret-1234567890")
        secret_approval = create_file_approval_request(secret_preview)
        secret_request = build_apply_request_from_approval(secret_approval.approval_id)
        secret_text = format_apply_request(secret_request)
        failures += emit("secret_like_content_blocks_apply", secret_approval.status == "blocked" and not secret_request.allowed)
        failures += emit("secret_like_content_not_exposed", "sk-test-secret" not in secret_text and clean_output(secret_text))

        events_text = format_file_approval_events(approved.approval_id)
        for event_name in (
            "sandbox_apply_requested",
            "sandbox_backup_created",
            "sandbox_apply_completed",
            "sandbox_verify_passed",
            "sandbox_rollback_completed",
        ):
            failures += emit(f"event_{event_name}_recorded", event_name in events_text, events=events_text)
        failures += emit("events_output_clean", clean_output(events_text), output=events_text)

        outputs = [executor_status, format_apply_request(request), result_text, verification_text, rollback_text, events_text]
        failures += emit("sandbox_outputs_clean", all(clean_output(text) for text in outputs))

        tools = ToolRegistry()
        command_cases = {
            "eva file apply executor status": "Sandbox only",
            "eva file apply sandbox policy": "No real project file",
            f"eva file approval sandbox apply {approved.approval_id}": "Sandbox only",
            f"eva file approval sandbox verify {approved.approval_id}": "Verification",
            f"eva file approval sandbox rollback {approved.approval_id}": "Rollback",
        }
        for command, expected in command_cases.items():
            handled = maybe_handle_fast_command(command, tools, {})
            text = handled[0] if handled else ""
            failures += emit(
                "cmd_" + command.replace(" ", "_").replace(".", "_").replace("-", "_")[:80],
                handled is not None and expected.lower() in text.lower() and "No real project file" in text and clean_output(text),
                output=text,
            )

        agent = FileAgent()
        failures += emit(
            "file_agent_execute_still_refuses_real_writes",
            agent.execute({"capability_id": "file.write", "input_summary": "write docs/REAL.md"}).status == "refused",
        )

        plan = create_task_plan("sandbox apply approved file change")
        plan_text = "\n".join(f"{step.step_type} {step.capability_id} {step.notes}" for step in plan.steps).lower()
        failures += emit(
            "planner_sandbox_apply_marks_sandbox_only_real_apply_unavailable",
            "sandbox" in plan_text and ("file.sandbox_apply_approved" in plan_text or "sandbox_apply" in plan_text) and not plan.can_execute_now,
            plan=plan.as_dict(),
        )
        review_text = format_team_review("sandbox apply this approval")
        failures += emit("team_review_routes_sandbox_apply_to_fileagent", "FileAgent" in review_text and "sandbox" in review_text.lower())

        registry = build_default_registry()
        for capability_id in (
            "file.apply_executor_status",
            "file.sandbox_apply_approved",
            "file.sandbox_verify_apply",
            "file.sandbox_rollback_apply",
            "file.sandbox_apply_policy",
        ):
            cap = registry.get(capability_id)
            permission = get_capability_permission(capability_id)
            resolution = resolve_capability(capability_id)
            schema = capability_to_tool_schema(capability_id)
            failures += emit(f"{capability_id}_registered", cap is not None)
            failures += emit(
                f"{capability_id}_permission_sandbox_runtime_only",
                permission is not None and permission.writes_local_data and not permission.public_mode_allowed and permission.private_mode_allowed and "sandbox" in permission.reason.lower(),
            )
            failures += emit(
                f"{capability_id}_resource_mapping",
                resolution.resource_id == "eva-file-agent-v1" and resolution.execution_path == "sandbox_only_executor",
            )
            failures += emit(f"{capability_id}_schema_exists", schema is not None)

        source_paths = [
            ROOT / "backend" / "eva" / "file_agent" / "apply_executor.py",
            ROOT / "backend" / "eva" / "file_agent" / "authority.py",
        ]
        source_text = "\n".join(path.read_text(encoding="utf-8", errors="replace").lower() for path in source_paths if path.exists())
        forbidden = [
            "from playwright",
            "import playwright",
            "sync_playwright",
            "async_playwright",
            "import pyautogui",
            "pyautogui.",
            "mcp.",
            "subprocess",
            "os.system",
            "popen",
            "document.cookie",
            "localstorage",
        ]
        failures += emit("no_forbidden_execution_imports", not any(pattern in source_text for pattern in forbidden))

        for script_name in [
            "verify_eva_file_agent_approval_ledger.py",
            "verify_eva_file_agent_write_safety.py",
            "verify_eva_file_agent_draft_preview.py",
            "verify_eva_file_agent_understanding.py",
            "verify_eva_file_agent_readonly.py",
            "verify_eva_agent_framework_quality.py",
            "verify_eva_planner_v3_quality.py",
            "verify_eva_capability_resource_mapping.py",
            "verify_eva_stabilization_v1.py",
        ]:
            failures += emit(f"existing_verifier_present_{script_name}", (ROOT / "scripts" / script_name).exists())

        failures += emit("no_real_target_created_or_modified", not real_target.exists())

    print(json.dumps({"overall_pass": failures == 0, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
