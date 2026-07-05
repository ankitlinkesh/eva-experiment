from __future__ import annotations

import io
import os
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def emit(case: str, passed: bool, **extra: object) -> int:
    payload = {"case": case, "pass": bool(passed), **extra}
    print(payload)
    return 0 if passed else 1


def clean_output(text: str) -> bool:
    bad = ("{'", "AuthorityDecision(", "NaturalRouteResult(", "Traceback", ".env.local contents")
    if any(marker in text for marker in bad):
        return False
    private_path = re.escape(str(ROOT))
    return re.search(private_path, text) is None


def run_fast_command(message: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    result = maybe_handle_fast_command(message, tools=ToolRegistry(), memory=None)
    if result is None:
        return ""
    return str(result[0])


def capture_main(module_main: object, *args: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = module_main(list(args))  # type: ignore[misc]
    return int(code or 0), buffer.getvalue()


def main() -> int:
    failures = 0
    temp = tempfile.TemporaryDirectory(prefix="eva_12g_")
    os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(Path(temp.name) / "approvals.sqlite3")
    os.environ["EVA_FILE_AGENT_APPLY_SANDBOX_ROOT"] = str(Path(temp.name) / "apply_sandbox")
    try:
        from backend.eva.authority.decision import (
            allow_draft_decision,
            allow_readonly_decision,
            allow_sandbox_decision,
            block_real_execution_decision,
            make_authority_decision,
            refuse_authority_decision,
        )
        from backend.eva.authority.formatter import format_authority_decision
        from backend.eva.authority.status import format_authority_status
        from backend.eva.core.natural_router import route_natural_request
    except Exception as exc:
        failures += emit("authority_and_router_imports", False, error=type(exc).__name__, detail=str(exc))
        return failures

    failures += emit("authority_and_router_imports", True)

    unknown = make_authority_decision(action_category="unknown", reason="test unknown")
    failures += emit("unknown_defaults_refused_or_preview", unknown.mode in {"refused", "preview_only"} and not unknown.real_execution_available)
    readonly = allow_readonly_decision(action_category="read", capability_id="file.project_inventory", agent_name="FileAgent", reason="safe read")
    failures += emit("readonly_allowed", readonly.allowed and readonly.mode == "read_only")
    draft = allow_draft_decision(action_category="draft", capability_id="file.draft_readme_section", agent_name="FileAgent", reason="draft output only")
    failures += emit("draft_allowed_draft_only", draft.allowed and draft.mode == "draft_only" and not draft.real_execution_available)
    sandbox = allow_sandbox_decision(action_category="sandbox_apply", capability_id="file.sandbox_apply_approved", agent_name="FileAgent", reason="sandbox only")
    failures += emit("sandbox_apply_sandbox_only", sandbox.allowed and sandbox.sandbox_only and not sandbox.real_execution_available)
    real_write = block_real_execution_decision(action_category="local_write", capability_id="file.real_apply", reason="real writes disabled")
    failures += emit("real_file_write_blocked", not real_write.allowed and real_write.mode == "real_execution_blocked")
    failures += emit("destructive_refused", not refuse_authority_decision(action_category="destructive", reason="no").allowed)
    failures += emit("external_send_refused", not refuse_authority_decision(action_category="external_send", reason="no").allowed)
    failures += emit("terminal_refused", not refuse_authority_decision(action_category="terminal", reason="no").allowed)
    failures += emit("browser_action_refused", not refuse_authority_decision(action_category="browser_action", reason="no").allowed)

    formatted = "\n\n".join([format_authority_status(), format_authority_decision(sandbox)])
    failures += emit("authority_output_clean", clean_output(formatted), output=formatted)

    examples = {
        "inspect this project": "project_inspect",
        "show pending approvals": "approval_pending",
        "sandbox apply the approved change": "approval_sandbox_apply",
        "verify the sandbox apply": "approval_sandbox_verify",
        "rollback the sandbox apply": "approval_sandbox_rollback",
    }
    for text, expected in examples.items():
        route = route_natural_request(text)
        failures += emit(f"route_{expected}", route.intent == expected, route=route.as_dict())

    delete_route = route_natural_request("delete my files")
    failures += emit("delete_files_refused_high_risk", delete_route.refusal_reason is not None and delete_route.authority_category == "destructive", route=delete_route.as_dict())

    ask_project = run_fast_command("eva ask inspect this project")
    failures += emit("eva_ask_project_inspect", "Project" in ask_project and "Authority decision" in ask_project and clean_output(ask_project), output=ask_project[:800])
    ask_pending = run_fast_command("eva ask show pending approvals")
    failures += emit("eva_ask_pending_approvals", "approval" in ask_pending.lower() and clean_output(ask_pending), output=ask_pending[:800])
    ask_safe = run_fast_command("eva ask what can Eva do safely right now")
    failures += emit("eva_ask_safe_capabilities", "safely" in ask_safe.lower() and "real execution" in ask_safe.lower() and clean_output(ask_safe), output=ask_safe[:800])
    ask_delete = run_fast_command("eva ask delete my files")
    failures += emit("eva_ask_delete_refuses", "refused" in ask_delete.lower() and "real execution" in ask_delete.lower(), output=ask_delete[:800])
    ask_sandbox_none = run_fast_command("eva ask sandbox apply the approved change")
    failures += emit("sandbox_apply_not_guessed_when_none", "approval" in ask_sandbox_none.lower() and ("no approved" in ask_sandbox_none.lower() or "specify" in ask_sandbox_none.lower()), output=ask_sandbox_none[:800])

    failures += emit("eva_ask_output_clean", all(clean_output(text) for text in (ask_project, ask_pending, ask_safe, ask_delete, ask_sandbox_none)))

    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.resource_mapping import resolve_capability_resource
    from backend.eva.capabilities.tool_schemas import get_tool_schema_preview

    for cap_id in ("eva.ask", "eva.natural_router", "eva.authority_status", "eva.authority_decision_preview", "eva.verify_all"):
        failures += emit(f"{cap_id}_registered", get_capability(cap_id) is not None)
    ask_permission = get_capability_permission("eva.ask")
    failures += emit("eva_ask_permission_no_real_write", ask_permission is not None and not ask_permission.writes_local_data and not ask_permission.requires_override)
    ask_resolution = resolve_capability_resource("eva.ask")
    failures += emit("eva_ask_resource_mapping", ask_resolution.resource_id == "eva-authority-router" and ask_resolution.available_now)
    ask_schema = get_tool_schema_preview("eva.ask")
    failures += emit("eva_ask_tool_schema", ask_schema is not None and ask_schema.get("name"))

    from backend.eva.planner.capability_selector import infer_goal_intents, select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    intents = infer_goal_intents("ask Eva to inspect this project")
    caps = select_capabilities_for_goal("ask Eva to inspect this project")
    failures += emit("planner_recognizes_natural_routing", "natural_request" in intents and "eva.ask" in caps, intents=intents, caps=caps)
    plan = create_task_plan("ask Eva to sandbox apply the approved change")
    plan_text = str(plan)
    failures += emit("planner_includes_authority_or_sandbox", "eva.ask" in plan_text or "sandbox" in plan_text.lower(), plan=plan.as_dict() if hasattr(plan, "as_dict") else plan_text[:800])
    review = format_team_review("ask Eva to sandbox apply the approved change")
    failures += emit("team_review_mentions_authority_decision", "authority" in review.lower() and "FileAgent" in review, output=review[:1000])

    try:
        import scripts.verify_eva_all as verify_all

        code, out = capture_main(verify_all.main, "--list")
        failures += emit("verify_all_imports_and_lists", code == 0 and "verify_eva_file_agent_sandbox_apply.py" in out and clean_output(out), output=out)
    except Exception as exc:
        failures += emit("verify_all_imports_and_lists", False, error=type(exc).__name__, detail=str(exc))

    for script in (
        "verify_eva_file_agent_sandbox_apply.py",
        "verify_eva_file_agent_approval_ledger.py",
        "verify_eva_file_agent_write_safety.py",
        "verify_eva_planner_v3_quality.py",
        "verify_eva_capability_resource_mapping.py",
        "verify_eva_stabilization_v1.py",
    ):
        failures += emit(f"existing_verifier_present_{script}", (ROOT / "scripts" / script).exists())

    print({"overall_pass": failures == 0, "failures": failures})
    temp.cleanup()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
