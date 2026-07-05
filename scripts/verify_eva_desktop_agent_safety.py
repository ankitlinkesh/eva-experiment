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
        "DesktopAgentStatus(",
        "DesktopActionSafetyDecision(",
        "DesktopAppRisk(",
        "DesktopCapabilityPreview(",
        "DesktopBlockedAction(",
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


def assert_desktop_safety_text(text: str, label: str) -> None:
    assert_clean(text, label)
    lower = text.lower()
    assert_true("desktopagent" in lower or "desktop agent" in lower or "real desktop observation mode" in lower or "real desktop control gate" in lower, f"{label} missing DesktopAgent/gate wording")
    assert_true("real desktop observation" in lower or "screen observation" in lower or "desktop mode is observation-only" in lower, f"{label} missing observation boundary")
    assert_true("real desktop control" in lower or "desktop control is not enabled" in lower or "no app or window control" in lower, f"{label} missing control boundary")
    assert_true("locked" in lower or "blocked" in lower or "not enabled" in lower or "no app or window control" in lower, f"{label} missing locked/blocked wording")
    assert_true("no screen" in lower or "no screenshot" in lower or "no desktop" in lower or "dry-run/control-gate only" in lower, f"{label} missing no-execution wording")


def main() -> int:
    from backend.eva.agents.team_review import format_team_review
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.desktop_agent.action_safety import evaluate_desktop_action_safety
    from backend.eva.desktop_agent.app_risk import classify_desktop_app_risk
    from backend.eva.desktop_agent.formatter import (
        format_desktop_action_safety,
        format_desktop_app_risk,
        format_desktop_blocked_actions,
        format_desktop_policy,
        format_desktop_readiness,
        format_desktop_status,
    )
    from backend.eva.desktop_agent.policy import get_desktop_capability_policy
    from backend.eva.desktop_agent.status import get_desktop_agent_status
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan

    status = get_desktop_agent_status()
    policy = get_desktop_capability_policy()
    assert_true(status.execution_enabled is False, "Desktop execution unexpectedly enabled")
    assert_true(policy.real_screen_observation_enabled is False, "Screen observation unexpectedly enabled")
    assert_true(policy.real_desktop_control_enabled is False, "Desktop control unexpectedly enabled")

    outputs = {
        "status": format_desktop_status(),
        "policy": format_desktop_policy(),
        "blocked": format_desktop_blocked_actions(),
        "action click": format_desktop_action_safety("click"),
        "action screenshot": format_desktop_action_safety("screenshot"),
        "app risk terminal": format_desktop_app_risk("terminal"),
        "readiness": format_desktop_readiness(),
    }
    for label, output in outputs.items():
        assert_desktop_safety_text(output, label)

    risky_actions = [
        "screen_capture",
        "screenshot",
        "app_launch",
        "mouse_move",
        "mouse_click",
        "mouse_drag",
        "keyboard_type",
        "hotkey",
        "clipboard_read",
        "clipboard_write",
        "file_dialog",
        "terminal_shell",
        "install_package",
        "external_send",
    ]
    for action in risky_actions:
        decision = evaluate_desktop_action_safety(action)
        assert_true(not decision.allowed_now, f"{action} unexpectedly allowed")
        assert_true(decision.decision in {"blocked", "locked"}, f"{action} not blocked/locked")
        text = format_desktop_action_safety(action)
        assert_desktop_safety_text(text, f"action {action}")

    app_risk = classify_desktop_app_risk("terminal")
    assert_true(app_risk.risk_level.value == "terminal_or_code_execution", "terminal risk not classified")
    assert_true(not app_risk.allowed_for_control_now, "terminal control unexpectedly allowed")

    commands = [
        "eva desktop status",
        "eva desktop policy",
        "eva desktop blocked actions",
        "eva desktop action safety click",
        "eva desktop action safety screenshot",
        "eva desktop app risk terminal",
        "eva desktop readiness",
        "eva ask can Eva control my desktop",
        "eva ask can Eva see my screen",
        "eva ask can Eva click and type",
        "eva ask can Eva use terminal",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_desktop_safety_text(output, command)

    routes = {
        "can Eva control my desktop": "desktop_control_policy",
        "can Eva see my screen": "desktop_observe_policy",
        "can Eva click and type": "desktop_action_safety",
        "can Eva use terminal": "desktop_action_safety",
        "show desktop policy": "desktop_policy",
        "what desktop actions are allowed": "desktop_policy",
        "is desktop control enabled": "desktop_status",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not status/read")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("DesktopAgent" in control, "Control Center missing DesktopAgent panel")
    assert_true("real desktop control" in control.lower(), "Control Center missing desktop control boundary")
    assert_true("real screen observation" in control.lower(), "Control Center missing screen observation boundary")
    assert_true("policy/readiness/action preview only" in control.lower(), "Control Center missing allowed-now desktop preview wording")

    for capability_id in (
        "desktop.status",
        "desktop.policy",
        "desktop.blocked_actions",
        "desktop.action_safety_preview",
        "desktop.app_risk",
        "desktop.readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-desktop-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("can Eva control my desktop and can it click")
    assert_true("desktop.status" in caps, "planner selector missed desktop.status")
    assert_true("desktop.action_safety_preview" in caps, "planner selector missed desktop action safety")
    plan = create_task_plan("show desktop policy")
    assert_true(any(step.capability_id == "desktop.policy" for step in plan.steps), "planner missing desktop policy step")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in plan.steps), "desktop safety plan contains executable/risky permission")
    review = format_team_review("can Eva click and type on my desktop")
    assert_clean(review, "team review")
    assert_true("DesktopAgent safety route" in review, "team review missing DesktopAgent safety route")
    assert_true("safety/status only" in review.lower(), "team review missing safety/status wording")

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
        "import mss",
        "from mss",
        "imagegrab",
        "screenshot(",
        "screencap(",
        "getwindowswithtitle",
        "getactivewindow",
        "enumwindows",
        "open_app(",
        "app.open",
        "mouse.",
        "keyboard.",
        "clipboard.",
        "pyperclip",
        "import subprocess",
        "subprocess.",
        "os.system",
        "pip install",
        "requests.",
        "httpx.",
        "urllib.request",
        "browser.launch",
        "page.goto",
        "read_text(\".env",
        "read_text('.env",
        ".cookies(",
        "context.cookies",
        "localstorage.getitem",
        "password_manager",
        "token_store",
    ]
    for token in forbidden:
        assert_true(token not in source_text, f"forbidden desktop execution/privacy code found: {token}")

    print("verify_eva_desktop_agent_safety: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
