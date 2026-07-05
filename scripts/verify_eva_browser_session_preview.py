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
        "BrowserSessionPreview(",
        "BrowserSessionRegistry(",
        "BrowserSessionReadiness(",
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
    from backend.eva.browser_agent.action_safety import evaluate_browser_action_safety
    from backend.eva.browser_agent.formatter import (
        format_browser_readiness,
        format_browser_session_latest,
        format_browser_session_plan,
        format_browser_session_preview,
        format_browser_session_status,
        format_browser_sessions,
    )
    from backend.eva.browser_agent.readiness import get_browser_session_readiness
    from backend.eva.browser_agent.session import create_preview_session
    from backend.eva.browser_agent.session_registry import get_latest_preview_session, list_preview_sessions
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    session = create_preview_session("Phase 13B verifier preview")
    assert_true(session.mode == "preview_only", "preview session mode is not preview_only")
    assert_true(session.status == "preview_planned", "preview session status is not preview_planned")
    assert_true("real browser control: locked" in " ".join(session.blocked_now).lower(), "session does not preserve locked boundary")

    sessions = list_preview_sessions()
    assert_true(any(item.session_id == session.session_id for item in sessions), "created preview session missing from registry")
    latest = get_latest_preview_session()
    assert_true(latest is not None, "latest preview session missing")
    assert_true(latest.mode == "preview_only", "latest session is not preview-only")

    readiness = get_browser_session_readiness()
    assert_true(readiness.ready_for_real_browser_control is False, "readiness unexpectedly enables browser control")
    assert_true(readiness.ready_for_readonly_mode is False, "read-only browser mode unexpectedly ready")

    for label, output in [
        ("session status", format_browser_session_status()),
        ("sessions", format_browser_sessions()),
        ("session preview", format_browser_session_preview()),
        ("session latest", format_browser_session_latest()),
        ("session plan", format_browser_session_plan()),
        ("readiness", format_browser_readiness()),
    ]:
        assert_clean(output, label)
        lower = output.lower()
        assert_true("browser" in lower, f"{label} missing browser wording")
        assert_true("session" in lower or label == "readiness", f"{label} missing session wording")
        assert_true("locked" in lower or "blocked" in lower or "preview" in lower, f"{label} missing locked/preview wording")
        assert_true("no real browser control" in lower or "real browser control: locked" in lower or "execution:" in lower, f"{label} missing no-execution boundary")

    commands = [
        "eva browser session status",
        "eva browser sessions",
        "eva browser session preview",
        "eva browser session latest",
        "eva browser session plan",
        "eva browser readiness",
        "eva ask start a browser session",
        "eva ask open a browser",
        "eva ask can Eva browse websites",
        "eva ask show browser session status",
        "eva ask what would a browser session do",
        "eva ask is browser read-only mode ready",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        lower = output.lower()
        assert_true("browser" in lower, f"{command} missing browser wording")
        assert_true("locked" in lower or "preview" in lower or "blocked" in lower, f"{command} missing locked/preview boundary")
        assert_true("launch" not in lower or "blocked" in lower or "no real browser" in lower, f"{command} implies browser launch")

    routes = {
        "start a browser session": "browser_session_preview",
        "open a browser": "browser_session_preview",
        "can Eva browse websites": "browser_session_status",
        "show browser session status": "browser_session_status",
        "what would a browser session do": "browser_session_plan",
        "is browser read-only mode ready": "browser_readonly_readiness",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not read/status")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real browser execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Browser Session Preview" in control, "Control Center missing Browser Session Preview panel")
    assert_true("session preview" in control.lower(), "Control Center missing session preview wording")
    assert_true("real browser control: locked" in control.lower() or "real browser control" in control.lower(), "Control Center missing locked browser control")

    for capability_id in (
        "browser.session_status",
        "browser.session_preview",
        "browser.sessions_list",
        "browser.session_plan",
        "browser.session_readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-browser-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("start a browser session and show browser session status")
    assert_true("browser.session_preview" in caps, "planner selector missed browser.session_preview")
    assert_true("browser.session_status" in caps, "planner selector missed browser.session_status")
    plan = create_task_plan("what would a browser session do")
    assert_true(any(step.capability_id == "browser.session_plan" for step in plan.steps), "planner missing browser session plan")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in plan.steps), "session plan contains executable/risky permission")
    review = format_team_review("start a browser session")
    assert_clean(review, "team review")
    assert_true("BrowserAgent session preview route" in review, "team review missing session preview route")
    assert_true("preview/status only" in review.lower(), "team review missing preview/status wording")

    for action in ("click", "type", "submit", "login", "payment", "file_upload", "download", "cookie_access", "local_storage_access", "profile_access"):
        decision = evaluate_browser_action_safety(action)
        assert_true(not decision.allowed_now, f"{action} unexpectedly allowed after session preview")

    source_files = [
        ROOT / "backend/eva/browser_agent",
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
        "import playwright",
        "from playwright",
        "import browser_use",
        "from browser_use",
        "import stagehand",
        "from stagehand",
        "import maxun",
        "from maxun",
        "import pyautogui",
        "from pyautogui",
        "import subprocess",
        "subprocess.",
        "requests.",
        "httpx.",
        "pip install",
        ".cookies(",
        "context.cookies",
        "localstorage.getitem",
        "local_storage_state",
        "browser.launch",
        "page.goto",
        "page.click",
        "page.fill",
        "page.screenshot",
    ]
    for token in forbidden:
        assert_true(token not in source_text, f"forbidden browser execution/privacy code found: {token}")

    print("verify_eva_browser_session_preview: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
