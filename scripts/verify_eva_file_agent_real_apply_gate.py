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
    blocked = (
        "{'",
        "RealApplyResult(",
        "RealApplyRequest(",
        "RealApplyEligibility(",
        "Traceback",
        ".env.local contents",
        str(ROOT).lower(),
    )
    return not any(marker.lower() in lowered for marker in blocked)


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
    temp_dir = Path(tempfile.mkdtemp(prefix="eva_phase12l_real_apply_"))
    os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(temp_dir / "approval_ledger.json")
    os.environ["EVA_FILE_AGENT_APPLY_SANDBOX_ROOT"] = str(temp_dir / "apply_sandbox")

    docs_target = ROOT / "docs" / "phase12l_real_apply_test.md"
    samples_target = ROOT / "samples" / "phase12l_real_apply_test.txt"
    changed_target = ROOT / "docs" / "phase12l_real_apply_changed.md"
    unrelated_target = ROOT / "docs" / "phase12l_unrelated_user_file.md"
    for path in (docs_target, samples_target, changed_target, unrelated_target):
        if path.exists():
            path.unlink()

    results: list[bool] = []
    try:
        from backend.eva.file_agent.real_apply import (
            build_real_apply_request_from_approval,
            create_real_text_file_from_approval,
            evaluate_real_apply_eligibility,
            format_real_apply_eligibility,
            format_real_apply_policy,
            format_real_apply_result,
            format_real_apply_rollback,
            format_real_apply_verification,
            rollback_real_text_file_apply,
            verify_real_text_file_apply,
        )
        from backend.eva.file_agent.approval_ledger import format_file_approval_events, get_file_approval_request

        results.append(report("real_apply_module_imports", True))
        policy = format_real_apply_policy()
        results.append(report("policy_says_create_new_text_only", "create-new-text-file only" in policy.lower()))

        safe_md = make_approval("docs/phase12l_real_apply_test.md", "Phase 12L docs create\n")
        safe_txt = make_approval("samples/phase12l_real_apply_test.txt", "Phase 12L samples create\n")
        results.append(report("docs_md_can_be_eligible", evaluate_real_apply_eligibility(safe_md.approval_id).allowed))
        results.append(report("samples_txt_can_be_eligible", evaluate_real_apply_eligibility(safe_txt.approval_id).allowed))

        docs_target.write_text("already here\n", encoding="utf-8")
        results.append(report("existing_target_refused", not evaluate_real_apply_eligibility(safe_md.approval_id).allowed))
        docs_target.unlink()

        for case, path in [
            ("py_refused", "docs/phase12l.py"),
            ("json_refused", "docs/phase12l.json"),
            ("toml_refused", "docs/phase12l.toml"),
            ("yaml_refused", "docs/phase12l.yaml"),
            ("yml_refused", "docs/phase12l.yml"),
            ("env_refused", ".env"),
            ("env_local_refused", ".env.local"),
            ("cfg_refused", "docs/phase12l.cfg"),
            ("ini_refused", "docs/phase12l.ini"),
            ("runtime_data_refused", "backend/eva/data/phase12l.md"),
            ("hidden_refused", "docs/.phase12l.md"),
            ("nested_unknown_folder_refused", "docs/new-folder/phase12l.md"),
            ("notes_folder_refused", "notes/phase12l.md"),
        ]:
            approval = make_approval(path, "safe text\n")
            results.append(report(case, not evaluate_real_apply_eligibility(approval.approval_id).allowed))

        binary = make_approval("docs/phase12l_binary.md", "hello\x00world")
        secret = make_approval("docs/phase12l_secret.md", "token sk-test1234567890 password hunter2")
        results.append(report("binary_content_refused", not evaluate_real_apply_eligibility(binary.approval_id).allowed))
        results.append(report("secret_content_refused", not evaluate_real_apply_eligibility(secret.approval_id).allowed))

        missing_phrase = create_real_text_file_from_approval(safe_md.approval_id, "")
        wrong_phrase = create_real_text_file_from_approval(safe_md.approval_id, "confirm")
        results.append(report("missing_confirmation_refused", not missing_phrase.ok and not docs_target.exists()))
        results.append(report("wrong_confirmation_refused", not wrong_phrase.ok and not docs_target.exists()))

        exact = f"confirm real create {safe_md.approval_id}"
        result = create_real_text_file_from_approval(safe_md.approval_id, exact)
        results.append(report("correct_confirmation_creates_file", result.ok and docs_target.exists()))
        results.append(report("created_content_matches_expected", docs_target.read_text(encoding="utf-8") == "Phase 12L docs create\n"))
        verification = verify_real_text_file_apply(result)
        results.append(report("verification_passes_after_create", verification.verified and verification.confidence >= 0.99))
        events = format_file_approval_events(safe_md.approval_id)
        results.append(report("audit_records_create_started_completed", "real_apply_create_started" in events and "real_apply_create_completed" in events))
        results.append(report("audit_records_verify_passed", "real_apply_verify_passed" in events))

        rollback_wrong = rollback_real_text_file_apply(safe_md.approval_id, "wrong")
        results.append(report("rollback_wrong_confirmation_refused", not rollback_wrong.success and docs_target.exists()))
        rollback_ok = rollback_real_text_file_apply(safe_md.approval_id, f"confirm rollback real create {safe_md.approval_id}")
        results.append(report("rollback_deletes_exact_eva_file", rollback_ok.success and not docs_target.exists()))

        changed = make_approval("docs/phase12l_real_apply_changed.md", "Original\n")
        changed_result = create_real_text_file_from_approval(changed.approval_id, f"confirm real create {changed.approval_id}")
        changed_target.write_text("Changed by user\n", encoding="utf-8")
        changed_rollback = rollback_real_text_file_apply(changed.approval_id, f"confirm rollback real create {changed.approval_id}")
        unrelated_target.write_text("user file\n", encoding="utf-8")
        results.append(report("rollback_refuses_changed_file", changed_result.ok and not changed_rollback.success and changed_target.exists()))
        results.append(report("rollback_does_not_delete_unrelated", unrelated_target.exists()))

        broad = run_fast_command("eva ask apply all my changes for real")
        ask_status = run_fast_command("eva ask what real actions can Eva do now?")
        ask_create = run_fast_command("eva ask create the approved text file")
        results.append(report("broad_real_apply_blocked", "blocked" in broad.lower() or "not eligible" in broad.lower()))
        results.append(report("ask_real_actions_explains_narrow_mode", "create-new-text-file only" in ask_status.lower()))
        results.append(report("ask_create_needs_confirmation_or_id", "confirm real create" in ask_create.lower() or "approval id" in ask_create.lower()))

        from backend.eva.capabilities.permissions import get_capability_permission
        from backend.eva.capabilities.registry import build_default_registry
        from backend.eva.capabilities.resource_mapping import resolve_capability_resource
        from backend.eva.capabilities.tool_schemas import get_tool_schema_preview
        from backend.eva.planner.capability_selector import infer_goal_intents, select_capabilities_for_goal
        from backend.eva.agents.team_review import format_team_review
        from backend.eva.control_center.collector import collect_control_center_status
        from backend.eva.control_center.formatter import format_control_center_status

        registry = build_default_registry()
        for cap_id in [
            "file.real_apply_policy",
            "file.real_apply_eligibility",
            "file.real_create_new_text_file",
            "file.real_verify_new_text_file",
            "file.real_rollback_new_text_file",
        ]:
            results.append(report(f"capability_{cap_id}", registry.get(cap_id) is not None))
            results.append(report(f"resource_{cap_id}", resolve_capability_resource(cap_id).resource_id == "eva-file-agent-v1"))
            results.append(report(f"schema_{cap_id}", get_tool_schema_preview(cap_id) is not None))
        permission = get_capability_permission("file.real_create_new_text_file")
        results.append(report("permission_high_confirmation_real", permission.risk_level == "high" and permission.requires_confirmation and not permission.read_only))
        results.append(report("planner_recognizes_narrow_real_create", "file_real_create" in infer_goal_intents("really create the approved docs file") and "file.real_create_new_text_file" in select_capabilities_for_goal("really create the approved docs file")))
        review = format_team_review("really create the approved docs file")
        results.append(report("team_review_mentions_fileagent_and_confirmation", "FileAgent" in review and "confirmation" in review.lower()))
        cc = format_control_center_status(collect_control_center_status())
        results.append(report("control_center_mentions_narrow_real_apply", "create-new-text-file only" in cc.lower()))

        output = "\n".join(
            [
                policy,
                format_real_apply_eligibility(evaluate_real_apply_eligibility(safe_txt.approval_id)),
                format_real_apply_result(result),
                format_real_apply_verification(verification),
                format_real_apply_rollback(rollback_ok),
                broad,
                ask_status,
                ask_create,
                review,
                cc,
            ]
        )
        results.append(report("output_no_raw_dict_repr", "{'" not in output))
        results.append(report("output_no_dataclass_repr", "RealApply" not in output))
        results.append(report("output_no_stack_trace", "Traceback" not in output))
        results.append(report("output_no_env_local_contents", ".env.local contents" not in output.lower()))
        results.append(report("output_no_absolute_private_paths", str(ROOT).lower() not in output.lower()))

        import scripts.verify_eva_all as verify_all

        all_scripts = set(verify_all.FULL_VERIFIERS) | set(verify_all.QUICK_VERIFIERS)
        results.append(report("master_includes_real_apply_gate", "verify_eva_file_agent_real_apply_gate.py" in all_scripts))

        approval = get_file_approval_request(safe_md.approval_id)
        results.append(report("approval_marked_real_create_consumed", getattr(approval, "status", "") == "consumed_by_real_create"))

    finally:
        for path in (docs_target, samples_target, changed_target, unrelated_target):
            if path.exists():
                path.unlink()
        shutil.rmtree(temp_dir, ignore_errors=True)

    overall = all(results)
    print({"overall_pass": overall, "failures": len([item for item in results if not item])})
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
