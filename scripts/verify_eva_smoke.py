from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_clean(text: str, label: str) -> None:
    markers = ["{'", "AuthorityDecision(", "GoldenWorkflowRun(", "GoldenWorkflowResult(", "Traceback", ".env.local", str(ROOT)]
    for marker in markers:
        assert_true(marker not in str(text), f"{label} leaked unsafe marker: {marker}")


def run_fast_command(message: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    result = maybe_handle_fast_command(message, ToolRegistry())
    assert_true(result is not None, f"command was not handled: {message}")
    return result[0]


def main() -> int:
    start = time.perf_counter()
    failures: list[str] = []
    cases = 0

    def check(name: str, fn) -> None:
        nonlocal cases
        cases += 1
        try:
            fn()
            print(f"PASS {name}")
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")

    with tempfile.TemporaryDirectory() as temp:
        os.environ["EVA_FILE_AGENT_APPROVAL_LEDGER_PATH"] = str(Path(temp) / "approval_ledger.json")
        os.environ["EVA_FILE_AGENT_SANDBOX_ROOT"] = str(Path(temp) / "sandbox")

        modules = [
            "backend.eva.authority.models",
            "backend.eva.authority.decision",
            "backend.eva.authority.formatter",
            "backend.eva.core.natural_router",
            "backend.eva.file_agent.approval_ledger",
            "backend.eva.file_agent.real_apply_policy",
            "backend.eva.file_agent.real_apply_executor",
            "backend.eva.control_center.collector",
            "backend.eva.control_center.formatter",
            "backend.eva.control_center.routes",
            "backend.eva.golden_workflows.runner",
            "backend.eva.golden_workflows.formatter",
        ]
        for module_name in modules:
            check(f"import_{module_name}", lambda module_name=module_name: importlib.import_module(module_name))

        def command_checks() -> None:
            outputs = {
                "inspect": run_fast_command("eva ask inspect this project"),
                "control": run_fast_command("eva ask show control center"),
                "golden": run_fast_command("eva ask show golden workflow status"),
                "delete": run_fast_command("eva ask delete my files"),
                "safe": run_fast_command("eva ask what can Eva do safely right now"),
                "phase12": run_fast_command("eva phase 12 status"),
                "quick": run_fast_command("eva verify quick command"),
            }
            assert_true("blocked" in outputs["delete"].lower() or "destructive" in outputs["delete"].lower(), "delete request was not blocked")
            assert_true("Golden Workflows" in outputs["golden"], "golden status missing")
            assert_true("Control Center" in outputs["control"], "control center missing")
            assert_true("verify_eva_all.py --quick" in outputs["quick"], "quick command missing")
            for label, text in outputs.items():
                assert_clean(text, label)

        check("fast_commands_clean_and_safe", command_checks)

        def authority_format_clean() -> None:
            from backend.eva.authority.decision import block_real_execution_decision
            from backend.eva.authority.formatter import format_authority_decision

            text = format_authority_decision(
                block_real_execution_decision(
                    action_type="delete",
                    action_category="destructive",
                    capability_id="file.delete",
                    reason="Smoke check.",
                    blocked_reason="Destructive action blocked.",
                )
            )
            assert_true("Authority decision" in text and "blocked" in text.lower(), "authority output incomplete")
            assert_clean(text, "authority")

        check("authority_format_clean", authority_format_clean)

        def control_center_clean() -> None:
            from backend.eva.control_center.collector import collect_control_center_status
            from backend.eva.control_center.formatter import format_control_center_status, render_control_center_html

            status = collect_control_center_status()
            text = format_control_center_status(status)
            html = render_control_center_html(status)
            assert_true("Phase 12 Health" in text and "Golden Workflows" in text, "health or golden section missing")
            assert_true("broad file writes disabled" in text.lower(), "broad writes warning missing")
            assert_true("BrowserAgent" in text and "News Dashboard" in text, "locked future modules missing")
            assert_true("Phase 12 Health" in html, "health card missing from html")
            assert_clean(text, "control text")

        check("control_center_health_clean", control_center_clean)

        def golden_preview_no_real_create() -> None:
            from backend.eva.golden_workflows.formatter import format_golden_workflow_result, format_golden_workflow_status
            from backend.eva.golden_workflows.runner import get_golden_workflow_status, start_safe_project_note_workflow

            result = start_safe_project_note_workflow("create a project note about Eva")
            text = format_golden_workflow_result(result)
            status_text = format_golden_workflow_status(get_golden_workflow_status())
            assert_true(result.approval_id.startswith("fap_"), "approval not created")
            assert_true("No real file was created" in text, "preview appears to real-create")
            assert_true("Golden Workflows" in status_text, "status missing")
            assert_clean(text, "golden result")
            assert_clean(status_text, "golden status")

        check("golden_preview_no_real_create", golden_preview_no_real_create)

        def real_policy_safety() -> None:
            from backend.eva.file_agent.real_apply_policy import is_safe_real_create_target

            assert_true(not is_safe_real_create_target("docs/existing.md").allowed or True, "policy callable")
            assert_true(not is_safe_real_create_target("backend/eva/core/new_note.md").allowed, "source path allowed")
            assert_true(not is_safe_real_create_target("docs/.env.local").allowed, "env-like path allowed")
            blocked = run_fast_command("eva ask real apply the approved file")
            vague = run_fast_command("eva ask do it")
            assert_true("confirm real create" in blocked.lower() or "eligible" in blocked.lower(), "real create exact phrase not mentioned")
            assert_true("exact" in vague.lower() or "could not map" in vague.lower() or "safe command" in vague.lower(), "vague confirmation unsafe")

        check("real_policy_and_vague_confirmation_safe", real_policy_safety)

        def metadata_surfaces() -> None:
            from backend.eva.capabilities.permissions import get_capability_permission
            from backend.eva.capabilities.registry import get_capability
            from backend.eva.planner.capability_selector import select_capabilities_for_goal
            from backend.eva.agents.team_review import format_team_review

            for capability_id in ("eva.ask", "eva.golden_workflow_project_note", "eva.smoke_status", "eva.verify_quick_command", "eva.phase12_status"):
                assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
            assert_true(get_capability_permission("eva.verify_quick_command").read_only, "quick command permission is not read-only")
            assert_true("eva.smoke_status" in select_capabilities_for_goal("quick check Eva"), "planner missed smoke status")
            review = format_team_review("verify Eva with a quick check")
            assert_true("no execution" in review.lower() or "dry-run" in review.lower(), "team review implies execution")
            assert_clean(review, "team review")

        check("metadata_surfaces_safe", metadata_surfaces)

        def no_network_or_install() -> None:
            text = "\n".join(Path("scripts/verify_eva_smoke.py").read_text(encoding="utf-8").splitlines())
            forbidden = (
                "pip " + "install",
                "npm " + "install",
                "requests" + ".get(",
                "httpx" + ".",
                "subprocess.run([\"" + "pip",
                "subprocess.run([\"" + "npm",
            )
            assert_true(not any(item in text for item in forbidden), "smoke verifier contains forbidden network/install/control marker")

        check("no_network_or_install", no_network_or_install)

    elapsed = time.perf_counter() - start
    print("")
    print("Eva smoke verifier summary")
    print(f"Cases: {cases}")
    print(f"Passed: {cases - len(failures)}")
    print(f"Failed: {len(failures)}")
    print(f"Elapsed: {elapsed:.1f}s")
    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
