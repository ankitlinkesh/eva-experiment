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
        "DesktopSessionPreview(",
        "DesktopAppStatusPreview(",
        "DesktopWindowStatusPreview(",
        "DesktopActiveContextPreview(",
        "DesktopObservationReadiness(",
        "DesktopSessionRegistryResult(",
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


def assert_desktop_preview_text(text: str, label: str) -> None:
    assert_clean(text, label)
    lower = text.lower()
    assert_true("desktop" in lower, f"{label} missing desktop wording")
    assert_true("preview" in lower or "status" in lower or "readiness" in lower, f"{label} missing preview/status wording")
    assert_true("locked" in lower or "blocked" in lower, f"{label} missing locked/blocked boundary")
    assert_true("no screen" in lower or "no real" in lower or "no desktop" in lower, f"{label} missing no-execution wording")


def main() -> int:
    from backend.eva.agents.team_review import format_team_review
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.desktop_agent.action_safety import evaluate_desktop_action_safety
    from backend.eva.desktop_agent.formatter import (
        format_desktop_active_context_preview,
        format_desktop_app_status_preview,
        format_desktop_observation_readiness,
        format_desktop_session_latest,
        format_desktop_session_plan,
        format_desktop_session_preview,
        format_desktop_session_status,
        format_desktop_sessions,
        format_desktop_window_status_preview,
    )
    from backend.eva.desktop_agent.readiness import get_desktop_observation_readiness
    from backend.eva.desktop_agent.session import create_preview_session
    from backend.eva.desktop_agent.session_registry import get_latest_preview_session, list_preview_sessions
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan

    session = create_preview_session("Phase 14B verifier preview")
    assert_true(session.mode == "preview_only", "preview session mode is not preview_only")
    assert_true(session.status == "preview_planned", "preview session status is not preview_planned")
    assert_true("real screen capture" in " ".join(session.blocked_now).lower(), "session does not preserve locked screen boundary")

    sessions = list_preview_sessions()
    assert_true(any(item.session_id == session.session_id for item in sessions), "created desktop preview session missing from registry")
    latest = get_latest_preview_session()
    assert_true(latest is not None, "latest desktop preview session missing")
    assert_true(latest.mode == "preview_only", "latest desktop session is not preview-only")

    readiness = get_desktop_observation_readiness()
    assert_true(readiness.ready_for_preview_records is True, "desktop preview records are not ready")
    assert_true(readiness.ready_for_real_observation is False, "real desktop observation unexpectedly ready")
    assert_true(readiness.ready_for_real_control is False, "real desktop control unexpectedly ready")

    outputs = {
        "session status": format_desktop_session_status(),
        "sessions": format_desktop_sessions(),
        "session preview": format_desktop_session_preview(),
        "session latest": format_desktop_session_latest(),
        "session plan": format_desktop_session_plan(),
        "app status preview": format_desktop_app_status_preview(),
        "window status preview": format_desktop_window_status_preview(),
        "active context preview": format_desktop_active_context_preview(),
        "observation readiness": format_desktop_observation_readiness(),
    }
    for label, output in outputs.items():
        assert_desktop_preview_text(output, label)

    commands = [
        "eva desktop session status",
        "eva desktop sessions",
        "eva desktop session preview",
        "eva desktop session latest",
        "eva desktop session plan",
        "eva desktop app status preview",
        "eva desktop window status preview",
        "eva desktop active context preview",
        "eva desktop observation readiness",
        "eva ask start a desktop session",
        "eva ask show desktop session status",
        "eva ask can Eva see open windows",
        "eva ask can Eva detect the active app",
        "eva ask can Eva inspect my screen",
        "eva ask what would desktop observation include",
        "eva ask is desktop observation ready",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_desktop_preview_text(output, command)
        lower = output.lower()
        assert_true("real desktop control" in lower or "real desktop observation" in lower or "real screen observation" in lower, f"{command} missing desktop lock boundary")

    routes = {
        "start a desktop session": "desktop_session_preview",
        "show desktop session status": "desktop_session_status",
        "can Eva see open windows": "desktop_window_status_preview",
        "can Eva detect the active app": "desktop_active_context_preview",
        "can Eva inspect my screen": "desktop_observation_readiness",
        "what would desktop observation include": "desktop_session_plan",
        "is desktop observation ready": "desktop_observation_readiness",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not preview/read")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real desktop execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Desktop Session Preview" in control, "Control Center missing Desktop Session Preview panel")
    assert_true("app/window schema preview" in control.lower(), "Control Center missing app/window schema preview wording")
    assert_true("active context" in control.lower(), "Control Center missing active context preview wording")

    for capability_id in (
        "desktop.session_status",
        "desktop.sessions_list",
        "desktop.session_preview",
        "desktop.session_plan",
        "desktop.app_status_preview",
        "desktop.window_status_preview",
        "desktop.active_context_preview",
        "desktop.observation_readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-desktop-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("start a desktop session and show open window preview")
    assert_true("desktop.session_preview" in caps, "planner selector missed desktop.session_preview")
    assert_true("desktop.window_status_preview" in caps, "planner selector missed desktop.window_status_preview")
    plan = create_task_plan("what would desktop observation include")
    assert_true(any(step.capability_id == "desktop.session_plan" for step in plan.steps), "planner missing desktop session plan")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in plan.steps), "desktop session plan contains executable/risky permission")
    review = format_team_review("can Eva see open windows")
    assert_clean(review, "team review")
    assert_true("DesktopAgent session preview route" in review, "team review missing desktop session preview route")
    assert_true("preview/status only" in review.lower(), "team review missing preview/status wording")

    for action in ("screen_capture", "screenshot", "app_launch", "mouse_click", "keyboard_type", "hotkey", "clipboard_read", "file_dialog", "terminal_shell"):
        decision = evaluate_desktop_action_safety(action)
        assert_true(not decision.allowed_now, f"{action} unexpectedly allowed after desktop session preview")

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

    print("verify_eva_desktop_session_preview: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
