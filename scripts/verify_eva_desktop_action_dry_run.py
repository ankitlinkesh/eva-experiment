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
        "DesktopActionDryRun(",
        "DesktopActionStepPreview(",
        "DesktopActionRisk(",
        "DesktopActionDryRunResult(",
        "DesktopActionPlanPreview(",
        "DesktopActionTargetPreview(",
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


def run_fast_command(command: str) -> str:
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry

    result = maybe_handle_fast_command(command, ToolRegistry())
    assert_true(result is not None, f"{command} was not handled")
    return result[0]


def main() -> int:
    from backend.eva.desktop_agent.action_dry_run import (
        create_desktop_action_dry_run,
        create_desktop_action_dry_run_result,
        create_desktop_action_plan_preview,
        get_desktop_action_approval_requirements,
    )
    from backend.eva.desktop_agent.formatter import (
        format_desktop_action_approvals,
        format_desktop_action_dry_run,
        format_desktop_action_plan,
        format_desktop_action_readiness,
        format_desktop_action_risk,
        format_desktop_dry_run_policy,
    )
    from backend.eva.desktop_agent.risk import DesktopActionRiskLevel, evaluate_desktop_action_risk
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    dry_run = create_desktop_action_dry_run("click the send button and type hello")
    assert_true(dry_run.execution_enabled is False, "desktop dry-run unexpectedly enables execution")
    assert_true(any(step.action_type == "mouse_click_preview" for step in dry_run.steps), "dry-run missing click preview")
    assert_true(any(step.action_type == "keyboard_type_preview" for step in dry_run.steps), "dry-run missing type preview")

    result = create_desktop_action_dry_run_result("press ctrl s")
    assert_true(result.executed is False, "dry-run result unexpectedly executed")
    assert_true(result.ready_for_real_control is False, "dry-run result says real control is ready")

    plan = create_desktop_action_plan_preview("open an app and send a message")
    assert_true(plan.mode == "dry_run_only", "plan preview mode is not dry-run only")
    assert_true(plan.real_desktop_execution == "locked", "plan preview does not lock desktop execution")
    assert_true(get_desktop_action_approval_requirements(), "approval requirements missing")

    blocked_actions = (
        "mouse click",
        "mouse move",
        "mouse drag",
        "type into app",
        "hotkey ctrl s",
        "clipboard read",
        "clipboard write",
        "launch app",
        "file dialog",
        "terminal command",
        "screen observation",
    )
    for action in blocked_actions:
        risk = evaluate_desktop_action_risk(action)
        assert_true(risk.executable_now is False, f"{action} unexpectedly executable")
        assert_true(risk.blocked_now is True, f"{action} not blocked")
        assert_true("preview" in risk.action_type, f"{action} missing preview action type")

    terminal = evaluate_desktop_action_risk("terminal")
    assert_true(terminal.level in {DesktopActionRiskLevel.CRITICAL_BLOCKED, DesktopActionRiskLevel.FORBIDDEN}, "terminal was not critical/forbidden")

    for label, output in [
        ("dry run", format_desktop_action_dry_run("click a button")),
        ("action plan", format_desktop_action_plan("open an app")),
        ("risk", format_desktop_action_risk("click")),
        ("approvals", format_desktop_action_approvals()),
        ("policy", format_desktop_dry_run_policy()),
        ("readiness", format_desktop_action_readiness()),
    ]:
        assert_clean(output, label)
        lower = output.lower()
        assert_true("desktop" in lower, f"{label} missing desktop wording")
        assert_true("dry-run" in lower or "dry run" in lower or "risk" in lower or "approval" in lower, f"{label} missing dry-run/risk wording")
        assert_true("real desktop control is locked" in lower or "execution:" in lower or "locked" in lower, f"{label} missing execution lock")

    commands = [
        "eva desktop action dry run click the send button",
        "eva desktop action plan open an app",
        "eva desktop action risk click",
        "eva desktop action approvals",
        "eva desktop dry run policy",
        "eva desktop action readiness",
        "eva ask dry run clicking a button",
        "eva ask what would Eva do to open an app",
        "eva ask can Eva click this",
        "eva ask can Eva type into an app",
        "eva ask can Eva press hotkeys",
        "eva ask plan desktop actions for sending a message",
        "eva ask what desktop actions need approval",
        "eva ask show desktop action dry run policy",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        lower = output.lower()
        assert_true("desktop" in lower, f"{command} missing desktop wording")
        assert_true("locked" in lower or "dry-run" in lower or "dry run" in lower or "blocked" in lower, f"{command} missing dry-run/locked boundary")

    routes = {
        "dry run clicking a button": "desktop_action_dry_run",
        "what would Eva do to open an app": "desktop_action_plan_preview",
        "can Eva click this": "desktop_action_risk",
        "can Eva type into an app": "desktop_action_risk",
        "can Eva press hotkeys": "desktop_action_risk",
        "plan desktop actions for sending a message": "desktop_action_plan_preview",
        "what desktop actions need approval": "desktop_action_approvals",
        "show desktop action dry run policy": "desktop_dry_run_policy",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not read/status")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real desktop execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Desktop Action Dry-Run" in control, "Control Center missing Desktop Action Dry-Run panel")
    assert_true("risk levels" in control.lower(), "Control Center missing risk levels")
    assert_true("approval" in control.lower(), "Control Center missing approval requirements")

    for capability_id in (
        "desktop.action_dry_run",
        "desktop.action_plan_preview",
        "desktop.action_risk",
        "desktop.action_approvals",
        "desktop.dry_run_policy",
        "desktop.action_readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-desktop-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("dry run clicking a button and can Eva press hotkeys")
    assert_true("desktop.action_dry_run" in caps, "planner selector missed desktop.action_dry_run")
    assert_true("desktop.action_risk" in caps, "planner selector missed desktop.action_risk")
    task_plan = create_task_plan("plan desktop actions for sending a message")
    assert_true(any(step.capability_id == "desktop.action_plan_preview" for step in task_plan.steps), "planner missing desktop action plan preview")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in task_plan.steps), "desktop dry-run plan contains executable/risky permission")
    review = format_team_review("plan desktop actions for sending a message")
    assert_clean(review, "team review")
    assert_true("DesktopAgent action dry-run route" in review, "team review missing action dry-run route")
    assert_true("dry-run/status only" in review.lower(), "team review missing dry-run/status wording")

    docs = [
        ROOT / "docs" / "EVA_CURRENT_STATE.md",
        ROOT / "docs" / "EVA_CAPABILITIES.md",
        ROOT / "docs" / "EVA_AGENT_FRAMEWORK.md",
        ROOT / "docs" / "EVA_THREAT_MODEL.md",
        ROOT / "docs" / "EVA_VERIFICATION.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        assert_true("Desktop Action Dry-Run" in text or "desktop action dry-run" in text.lower(), f"{doc.name} missing desktop action dry-run docs")

    source_files = [
        ROOT / "backend/eva/desktop_agent",
        ROOT / "backend/eva/core/natural_router.py",
    ]
    source_text = ""
    for path in source_files:
        if path.is_dir():
            for child in path.rglob("*.py"):
                source_text += child.read_text(encoding="utf-8").lower() + "\n"
        elif path.exists():
            source_text += path.read_text(encoding="utf-8").lower() + "\n"
    forbidden = [
        "import pyautogui",
        "from pyautogui",
        "import playwright",
        "from playwright",
        "import browser_use",
        "from browser_use",
        "import stagehand",
        "from stagehand",
        "import maxun",
        "from maxun",
        "import subprocess",
        "subprocess.",
        "os.system",
        "pip install",
        "requests.",
        "httpx.",
        "urllib.request",
        "imagegrab",
        "pytesseract",
        "easyocr",
        "mss.",
        "cv2.",
        "screenshot(",
        "screencap(",
        "getwindowswithtitle",
        "getactivewindow",
        "enumwindows",
        "open_app(",
        "mouse.",
        "keyboard.",
        "pyperclip",
        "clipboard.",
        ".cookies(",
        "context.cookies",
        "localstorage.getitem",
        "read_text('.env",
        'read_text(".env',
    ]
    for token in forbidden:
        assert_true(token not in source_text, f"forbidden desktop execution/privacy code found: {token}")

    print("verify_eva_desktop_action_dry_run: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
