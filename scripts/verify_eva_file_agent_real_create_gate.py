from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def report(case: str, passed: bool, **extra: object) -> bool:
    payload = {"case": case, "pass": bool(passed)}
    payload.update(extra)
    print(payload)
    return bool(passed)


def clean_output(text: str) -> bool:
    lowered = str(text or "").lower()
    return not any(
        marker.lower() in lowered
        for marker in (
            "{'",
            "RealApplyResult(",
            "RealApplyRequest(",
            "Traceback",
            ".env.local contents",
            str(ROOT).lower(),
        )
    )


def run_fast_command(message: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    handled = maybe_handle_fast_command(message, ToolRegistry(), session_context={}, memory=None)
    return handled[0] if handled else ""


def make_approval(path: str, text: str, *, approve: bool = True) -> object:
    from backend.eva.file_agent.approval_ledger import approve_file_approval_request, create_file_approval_request
    from backend.eva.file_agent.draft_preview import create_file_draft_preview

    draft = create_file_draft_preview(path, text, repo_root=ROOT)
    approval = create_file_approval_request(draft, repo_root=ROOT)
    if approve:
        approval = approve_file_approval_request(approval.approval_id, approval.required_confirmation_phrase)
    return approval


def main() -> int:
    temp_dir = Path(tempfile.mkdtemp(prefix="eva_real_create_gate_"))
    ledger_path = temp_dir / "approval_ledger.json"
    sandbox_root = temp_dir / "apply_sandbox"
    os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(ledger_path)
    os.environ["EVA_FILE_AGENT_APPLY_SANDBOX_ROOT"] = str(sandbox_root)

    test_docs_file = ROOT / "docs" / "phase12i_test_real_create.md"
    test_samples_file = ROOT / "samples" / "phase12i_test_real_create.txt"
    changed_file = ROOT / "docs" / "phase12i_test_changed.md"
    user_file = ROOT / "docs" / "phase12i_user_created.md"
    for path in (test_docs_file, test_samples_file, changed_file, user_file):
        if path.exists():
            path.unlink()

    results: list[bool] = []
    try:
        from backend.eva.file_agent.real_apply_policy import (
            evaluate_real_apply_eligibility,
            format_real_apply_eligibility,
            format_real_apply_policy,
            is_allowed_real_create_extension,
            is_allowed_real_create_parent,
            is_existing_file_blocked,
            is_safe_real_create_target,
        )
        from backend.eva.file_agent.real_apply_executor import (
            apply_real_create,
            build_real_create_request_from_approval,
            format_real_apply_result,
            format_real_apply_status,
            format_real_apply_verification,
            format_real_create_request,
            format_real_apply_rollback,
            rollback_real_create,
            verify_real_create,
        )
        from backend.eva.authority.formatter import format_authority_decision
        from backend.eva.file_agent.approval_ledger import (
            approve_file_approval_request,
            cancel_file_approval_request,
            deny_file_approval_request,
            expire_old_file_approvals,
            format_file_approval_events,
            get_file_approval_request,
        )
        from backend.eva.file_agent.draft_preview import create_file_draft_preview
        from backend.eva.file_agent.approval_ledger import create_file_approval_request

        results.append(report("real_apply_policy_imports", True))
        results.append(report("real_apply_executor_imports", True))

        results.append(report("policy_allows_docs_md", is_safe_real_create_target("docs/new_note.md", repo_root=ROOT).allowed))
        results.append(report("policy_allows_samples_txt", is_safe_real_create_target("samples/new_note.txt", repo_root=ROOT).allowed))
        existing = ROOT / "docs" / "EVA_FILE_AGENT.md"
        results.append(report("policy_blocks_existing_files", is_existing_file_blocked(str(existing), repo_root=ROOT)))
        results.append(report("policy_blocks_overwrite", not is_safe_real_create_target("docs/EVA_FILE_AGENT.md", repo_root=ROOT).allowed))
        for case, path in [
            ("policy_blocks_py", "docs/new_note.py"),
            ("policy_blocks_json", "docs/new_note.json"),
            ("policy_blocks_env", ".env"),
            ("policy_blocks_env_local", ".env.local"),
            ("policy_blocks_hidden", "docs/.hidden.md"),
            ("policy_blocks_backend", "backend/new_note.md"),
            ("policy_blocks_scripts", "scripts/new_note.md"),
            ("policy_blocks_runtime_data", "backend/eva/data/new_note.md"),
            ("policy_blocks_absolute", str(ROOT / "docs" / "absolute.md")),
            ("policy_blocks_traversal", "docs/../samples/traversal.md"),
        ]:
            results.append(report(case, not is_safe_real_create_target(path, repo_root=ROOT).allowed))
        results.append(report("policy_extension_helper", is_allowed_real_create_extension("notes.md") and not is_allowed_real_create_extension("notes.py")))
        results.append(report("policy_parent_helper", is_allowed_real_create_parent("docs/new_note.md", repo_root=ROOT) and not is_allowed_real_create_parent("backend/new_note.md", repo_root=ROOT)))

        secret_approval = make_approval("docs/secret_real_create.md", "token sk-test1234567890 password hunter2", approve=True)
        results.append(report("policy_blocks_secret_like_content", not evaluate_real_apply_eligibility(secret_approval.approval_id, repo_root=ROOT).allowed))

        pending = make_approval("docs/pending_real_create.md", "Pending", approve=False)
        denied = deny_file_approval_request(make_approval("docs/denied_real_create.md", "Denied", approve=False).approval_id, "test")
        cancelled = cancel_file_approval_request(make_approval("docs/cancelled_real_create.md", "Cancelled", approve=False).approval_id, "test")
        expired_pending = make_approval("docs/expired_real_create.md", "Expired", approve=False)
        expire_old_file_approvals(max_age_minutes=0)
        for case, approval in [
            ("eligibility_refuses_pending", pending),
            ("eligibility_refuses_denied", denied),
            ("eligibility_refuses_cancelled", cancelled),
            ("eligibility_refuses_expired", expired_pending),
        ]:
            results.append(report(case, not evaluate_real_apply_eligibility(approval.approval_id, repo_root=ROOT).allowed))

        approved = make_approval("docs/phase12i_test_real_create.md", "Phase 12I real create test\n", approve=True)
        eligibility = evaluate_real_apply_eligibility(approved.approval_id, repo_root=ROOT)
        results.append(report("eligibility_accepts_safe_md", eligibility.allowed and eligibility.approval_id == approved.approval_id))
        results.append(report("eligibility_format_clean", clean_output(format_real_apply_eligibility(eligibility)) and "confirm real create" in format_real_apply_eligibility(eligibility)))

        request = build_real_create_request_from_approval(approved.approval_id, confirmation_phrase="")
        results.append(report("real_create_refuses_without_confirmation", not request.allowed and "confirm real create" in format_real_create_request(request)))
        vague = build_real_create_request_from_approval(approved.approval_id, confirmation_phrase="yes")
        results.append(report("real_create_refuses_vague_confirmation", not vague.allowed))

        exact_phrase = f"confirm real create {approved.approval_id}"
        request = build_real_create_request_from_approval(approved.approval_id, confirmation_phrase=exact_phrase)
        results.append(report("global_authority_allows_safe_real_create", request.authority.mode == "real_execution_allowed" and request.authority.risk_level == "high" and request.authority.requires_approval))
        result = apply_real_create(request)
        results.append(report("real_create_succeeds_exact_phrase", result.ok and test_docs_file.exists()))
        results.append(report("real_create_result_clean", clean_output(format_real_apply_result(result))))
        results.append(report("created_content_verifies", test_docs_file.read_text(encoding="utf-8") == "Phase 12I real create test\n"))
        results.append(report("no_existing_file_edited", existing.exists()))
        results.append(report("no_source_file_edited", (ROOT / "backend" / "eva" / "main.py").exists()))
        events = format_file_approval_events(approved.approval_id)
        results.append(report("ledger_records_real_create_events", all(marker in events for marker in ("real_create_requested", "real_create_completed"))))
        consumed = get_file_approval_request(approved.approval_id)
        results.append(report("approval_marked_consumed", getattr(consumed, "status", "") == "consumed_by_real_create"))
        second = apply_real_create(build_real_create_request_from_approval(approved.approval_id, confirmation_phrase=exact_phrase))
        results.append(report("same_approval_cannot_apply_twice", not second.ok))
        verification = verify_real_create(approved.approval_id)
        results.append(report("verify_passes_after_create", verification.verified and verification.confidence >= 0.99))
        results.append(report("verification_output_clean", clean_output(format_real_apply_verification(verification))))
        rollback_refused = rollback_real_create(approved.approval_id, confirmation_phrase="")
        results.append(report("rollback_refuses_without_phrase", not rollback_refused.success))
        rollback = rollback_real_create(approved.approval_id, confirmation_phrase=f"confirm rollback real create {approved.approval_id}")
        results.append(report("rollback_succeeds_exact_phrase", rollback.success and not test_docs_file.exists()))
        results.append(report("rollback_removes_only_eva_file", "Rollback removed only the Eva-created file" in format_real_apply_rollback(rollback)))

        changed = make_approval("docs/phase12i_test_changed.md", "Original\n", approve=True)
        changed_req = build_real_create_request_from_approval(changed.approval_id, confirmation_phrase=f"confirm real create {changed.approval_id}")
        changed_result = apply_real_create(changed_req)
        changed_file.write_text("User changed after create\n", encoding="utf-8")
        changed_rollback = rollback_real_create(changed.approval_id, confirmation_phrase=f"confirm rollback real create {changed.approval_id}")
        results.append(report("rollback_refuses_changed_file", changed_result.ok and not changed_rollback.success and changed_file.exists()))

        user_file.write_text("User-created\n", encoding="utf-8")
        user_rollback = rollback_real_create("fap_user_created", confirmation_phrase="confirm rollback real create fap_user_created")
        results.append(report("rollback_refuses_user_created_file", not user_rollback.success and user_file.exists()))

        consumed_eligibility = evaluate_real_apply_eligibility(approved.approval_id, repo_root=ROOT)
        results.append(report("eligibility_refuses_consumed", not consumed_eligibility.allowed))

        blocked_authority = build_real_create_request_from_approval(secret_approval.approval_id, confirmation_phrase=f"confirm real create {secret_approval.approval_id}").authority
        results.append(report("global_authority_blocks_broad_write", blocked_authority.mode != "real_execution_allowed" and not blocked_authority.allowed))
        results.append(report("authority_output_clean", clean_output(format_authority_decision(request.authority))))

        ask_no_phrase = run_fast_command("eva ask real apply the approved file")
        results.append(report("eva_ask_requires_exact_phrase", "confirm real create" in ask_no_phrase and clean_output(ask_no_phrase)))

        approved2 = make_approval("samples/phase12i_test_real_create.txt", "Sample real create\n", approve=True)
        ask_apply = run_fast_command(f"eva ask confirm real create {approved2.approval_id}")
        results.append(report("eva_ask_confirm_real_create_applies", "Real create completed" in ask_apply and test_samples_file.exists() and clean_output(ask_apply)))
        ask_rollback = run_fast_command(f"eva ask confirm rollback real create {approved2.approval_id}")
        results.append(report("eva_ask_confirm_rollback_real_create", "Rollback removed only the Eva-created file" in ask_rollback and not test_samples_file.exists() and clean_output(ask_rollback)))

        status_text = format_real_apply_status()
        policy_text = format_real_apply_policy()
        results.append(report("status_and_policy_clean", clean_output(status_text + policy_text) and "narrow" in policy_text.lower()))

        from backend.eva.core.natural_router import route_natural_request
        route = route_natural_request("real apply this approved new file")
        results.append(report("natural_router_recognizes_real_create", route.intent == "real_create_request"))

        from backend.eva.control_center.collector import collect_control_center_status
        from backend.eva.control_center.formatter import format_control_center_status, render_control_center_html

        cc_text = format_control_center_status(collect_control_center_status())
        cc_html = render_control_center_html(collect_control_center_status())
        results.append(report("control_center_mentions_real_gate", "Narrow Real Apply Gate" in cc_text + cc_html))
        results.append(report("control_center_says_no_overwrite", "Existing files cannot be edited or overwritten" in cc_text + cc_html))

        from backend.eva.capabilities.permissions import get_capability_permission
        from backend.eva.capabilities.registry import build_default_registry
        from backend.eva.capabilities.resource_mapping import resolve_capability_resource
        from backend.eva.capabilities.tool_schemas import get_tool_schema_preview
        for cap_id in [
            "file.real_apply_policy",
            "file.real_create_eligibility",
            "file.real_create_safe_text",
            "file.real_create_verify",
            "file.real_create_rollback",
        ]:
            cap = build_default_registry().get(cap_id)
            permission = get_capability_permission(cap_id)
            results.append(report(f"capability_registered_{cap_id}", cap is not None))
            if cap_id == "file.real_create_safe_text":
                results.append(report("real_create_permission_medium_local_write", permission.risk_level == "medium" and not permission.read_only and permission.requires_confirmation))
            results.append(report(f"resource_mapping_{cap_id}", resolve_capability_resource(cap_id).resource_id == "eva-file-agent-v1"))
            results.append(report(f"tool_schema_{cap_id}", get_tool_schema_preview(cap_id) is not None))

        from backend.eva.planner.capability_selector import infer_goal_intents, select_capabilities_for_goal
        from backend.eva.agents.team_review import format_team_review

        results.append(report("planner_recognizes_real_create", "file_real_create" in infer_goal_intents("real apply approved text file") and "file.real_create_safe_text" in select_capabilities_for_goal("real apply approved text file")))
        review = format_team_review("real apply approved text file")
        results.append(report("team_review_routes_real_create_fileagent", "FileAgent" in review and "exact confirmation" in review.lower()))

        outputs = "\n".join([ask_no_phrase, ask_apply, ask_rollback, status_text, policy_text, cc_text, cc_html, review])
        results.append(report("output_no_raw_dict_repr", "{'" not in outputs))
        results.append(report("output_no_dataclass_repr", "RealApply" not in outputs))
        results.append(report("output_no_stack_trace", "Traceback" not in outputs))
        results.append(report("output_no_env_local_contents", ".env.local contents" not in outputs.lower()))
        results.append(report("output_no_absolute_private_paths", str(ROOT).lower() not in outputs.lower()))

        import scripts.verify_eva_all as verify_all
        results.append(report("master_verifier_includes_real_create_gate", "verify_eva_file_agent_real_create_gate.py" in verify_all.VERIFIERS))
        results.append(report("existing_control_center_verifier_present", (ROOT / "scripts" / "verify_eva_control_center.py").exists()))
        results.append(report("existing_authority_verifier_present", (ROOT / "scripts" / "verify_eva_authority_natural_router.py").exists()))
        results.append(report("existing_sandbox_verifier_present", (ROOT / "scripts" / "verify_eva_file_agent_sandbox_apply.py").exists()))
        results.append(report("existing_approval_verifier_present", (ROOT / "scripts" / "verify_eva_file_agent_approval_ledger.py").exists()))
        results.append(report("existing_write_safety_verifier_present", (ROOT / "scripts" / "verify_eva_file_agent_write_safety.py").exists()))
        results.append(report("existing_stabilization_verifier_present", (ROOT / "scripts" / "verify_eva_stabilization_v1.py").exists()))

    finally:
        for path in (test_docs_file, test_samples_file, changed_file, user_file):
            if path.exists():
                path.unlink()
        shutil.rmtree(temp_dir, ignore_errors=True)

    overall = all(results)
    print({"overall_pass": overall, "failures": len([item for item in results if not item])})
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
