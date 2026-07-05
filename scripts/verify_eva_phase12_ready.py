from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def assert_true(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_clean(text: str, label: str) -> None:
    forbidden = [
        "{'",
        "Phase12ReadyStatus(",
        "Traceback",
        "C:\\Users\\",
        ".env.local",
        "api_key",
        "Bearer ",
        "sk-",
        str(ROOT),
    ]
    for token in forbidden:
        assert_true(token not in text, f"{label} leaked unsafe/internal token: {token}")


def assert_phase12_boundary(text: str, label: str) -> None:
    lower = text.lower()
    assert_true("12l narrow real create" in lower or "phase 12l" in lower, f"{label} missing 12L narrow-create boundary")
    assert_true(".md/.txt" in text or ".md or .txt" in text, f"{label} missing safe text extension boundary")
    for word in ("broad", "source", "browser", "desktop", "shell", "mcp", "cloud"):
        assert_true(word in lower, f"{label} missing locked wording for {word}")
    assert_true("status" in lower or "audit" in lower, f"{label} does not identify status/audit nature")


def run_fast_command(command: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    result = maybe_handle_fast_command(command, ToolRegistry())
    assert_true(result is not None, f"{command} was not handled")
    return result[0]


def main() -> int:
    from backend.eva.agents.team_review import format_team_review
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.core.phase12_ready import (
        format_phase12_limits,
        format_phase12_proof,
        format_phase12_ready,
        format_phase12_summary,
    )
    from backend.eva.golden_workflows.status import format_golden_workflow_proof
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.skills.reality_check import format_project_proof
    from backend.eva.work_sessions.formatter import format_work_sessions_status

    for label, output in [
        ("ready", format_phase12_ready()),
        ("summary", format_phase12_summary()),
        ("limits", format_phase12_limits()),
        ("proof", format_phase12_proof()),
    ]:
        assert_clean(output, label)
        assert_phase12_boundary(output, label)
        assert_true("verifier" in output.lower() or "verify_eva_all.py" in output, f"{label} missing verifier proof wording")

    commands = [
        "eva phase 12 ready",
        "eva phase 12 summary",
        "eva phase 12 limits",
        "eva phase 12 proof",
        "eva ask is phase 12 ready",
        "eva ask summarize phase 12",
        "eva ask what are phase 12 limits",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        assert_phase12_boundary(output, command)
        if command.startswith("eva ask"):
            assert_true("Eva ask" in output and "Work session:" in output, f"{command} missing natural UX wrapper/session")

    routes = {
        "is phase 12 ready": "phase12_ready",
        "summarize phase 12": "phase12_summary",
        "what are phase 12 limits": "phase12_limits",
        "show phase 12 proof": "phase12_proof",
    }
    for prompt, intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == intent, f"{prompt!r} routed to {route.intent}, expected {intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not read/status")

    control = format_control_center_text()
    work = format_work_sessions_status()
    golden = format_golden_workflow_proof()
    project = format_project_proof()
    for label, output in [("control", control), ("work", work), ("golden", golden), ("project", project)]:
        assert_clean(output, label)
    assert_true("real file writes limited to approved new .md/.txt files" in control, "Control Center lost 12L write boundary")
    assert_true("Session tracking does not enable any new execution path" in work, "WorkSession status lost audit-only wording")
    assert_true("Phase 12L" in golden or "12L" in golden, "Golden proof lost narrow real-create wording")
    assert_true("does not unlock broad file edits" in project.lower() or "broad file edits" in project.lower(), "Project proof lost broad-edit warning")

    for capability_id in ("eva.phase12_ready", "eva.phase12_summary", "eva.phase12_limits", "eva.phase12_proof"):
        assert_true(get_capability(capability_id) is not None, f"capability missing: {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only metadata")
        assert_true(resolve_capability(capability_id).resource_id, f"resource mapping missing: {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"tool schema missing: {capability_id}")

    caps = select_capabilities_for_goal("is phase 12 ready and what are the limits")
    assert_true("eva.phase12_ready" in caps, "planner selector missed phase12 ready")
    assert_true("eva.phase12_limits" in caps, "planner selector missed phase12 limits")
    plan = create_task_plan("show phase 12 proof")
    assert_true(any(step.capability_id == "eva.phase12_proof" for step in plan.steps), "planner plan missing phase12 proof")
    review = format_team_review("is phase 12 ready")
    assert_clean(review, "team review")
    assert_true("Phase 12 readiness route" in review, "team review missing Phase 12 readiness route")
    assert_true("read-only" in review.lower() or "status" in review.lower(), "team review missing read-only/status wording")

    source_files = [
        ROOT / "backend/eva/core/phase12_ready.py",
        ROOT / "backend/eva/core/natural_router.py",
        ROOT / "backend/eva/planner/capability_selector.py",
    ]
    joined = "\n".join(path.read_text(encoding="utf-8") for path in source_files if path.exists()).lower()
    for forbidden in ["import playwright", "from playwright", "import pyautogui", "from pyautogui", "import subprocess", "subprocess.", "requests.", "httpx.", "pip install"]:
        assert_true(forbidden not in joined, f"forbidden execution code found: {forbidden}")

    print("verify_eva_phase12_ready: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
