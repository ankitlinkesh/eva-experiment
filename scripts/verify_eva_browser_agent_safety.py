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
        "BrowserAgentStatus(",
        "BrowserActionSafetyDecision(",
        "BrowserDomainPolicy(",
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
    from backend.eva.browser_agent.domain_policy import get_default_domain_policy
    from backend.eva.browser_agent.formatter import (
        format_browser_action_safety,
        format_browser_blocked_actions,
        format_browser_domain_policy,
        format_browser_policy,
        format_browser_readiness,
        format_browser_status,
    )
    from backend.eva.browser_agent.policy import get_browser_session_policy
    from backend.eva.browser_agent.status import get_browser_agent_status
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    status = get_browser_agent_status()
    policy = get_browser_session_policy()
    domain_policy = get_default_domain_policy()
    assert_true(status.execution_enabled is False, "Browser execution unexpectedly enabled")
    assert_true(policy.real_browser_control_enabled is False, "Real browser control unexpectedly enabled")
    assert_true(domain_policy.cookies_allowed is False, "Cookie access unexpectedly allowed")
    assert_true(domain_policy.local_storage_allowed is False, "localStorage access unexpectedly allowed")

    for label, output in [
        ("status", format_browser_status()),
        ("policy", format_browser_policy()),
        ("blocked", format_browser_blocked_actions()),
        ("domain", format_browser_domain_policy()),
        ("readiness", format_browser_readiness()),
        ("action click", format_browser_action_safety("click")),
    ]:
        assert_clean(output, label)
        lower = output.lower()
        assert_true("browseragent" in lower or "browser agent" in lower, f"{label} missing BrowserAgent wording")
        assert_true("locked" in lower or "blocked" in lower or "disabled" in lower, f"{label} missing locked/blocked wording")
        assert_true("no real browser control" in lower or "real browser control: locked" in lower or "execution: status" in lower, f"{label} missing no-execution boundary")

    risky_actions = [
        "click",
        "type",
        "submit",
        "login",
        "payment",
        "file_upload",
        "download",
        "cookie_access",
        "local_storage_access",
        "profile_access",
        "external_send",
    ]
    for action in risky_actions:
        decision = evaluate_browser_action_safety(action)
        assert_true(not decision.allowed_now, f"{action} unexpectedly allowed")
        assert_true(decision.decision in {"blocked", "locked"}, f"{action} not blocked/locked")
        text = format_browser_action_safety(action)
        assert_clean(text, f"action {action}")
        assert_true("blocked" in text.lower() or "locked" in text.lower(), f"{action} output missing blocked wording")

    commands = [
        "eva browser status",
        "eva browser policy",
        "eva browser blocked actions",
        "eva browser domain policy",
        "eva browser action safety click",
        "eva browser readiness",
        "eva ask can Eva use the browser",
        "eva ask what browser actions are allowed",
        "eva ask is browser control enabled",
        "eva ask show browser policy",
        "eva ask can Eva click login or upload files",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        lower = output.lower()
        assert_true("browser" in lower, f"{command} missing browser wording")
        assert_true("locked" in lower or "blocked" in lower or "disabled" in lower, f"{command} missing safety state")

    routes = {
        "can Eva use the browser": "browser_status",
        "what browser actions are allowed": "browser_policy",
        "is browser control enabled": "browser_status",
        "show browser policy": "browser_policy",
        "can Eva click login or upload files": "browser_action_safety",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not status/read")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("BrowserAgent" in control, "Control Center missing BrowserAgent panel")
    assert_true("real browser control: locked" in control.lower() or "real browser control" in control.lower(), "Control Center missing browser locked status")
    assert_true("policy/readiness/action preview" in control.lower(), "Control Center missing allowed-now browser preview wording")

    for capability_id in (
        "browser.status",
        "browser.policy",
        "browser.blocked_actions",
        "browser.domain_policy",
        "browser.action_safety_preview",
        "browser.readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-browser-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("can Eva use the browser and can it click")
    assert_true("browser.status" in caps, "planner selector missed browser.status")
    assert_true("browser.action_safety_preview" in caps, "planner selector missed browser action safety")
    plan = create_task_plan("show browser policy")
    assert_true(any(step.capability_id == "browser.policy" for step in plan.steps), "planner missing browser policy step")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in plan.steps), "browser safety plan contains executable/risky permission")
    review = format_team_review("can Eva click login or upload files")
    assert_clean(review, "team review")
    assert_true("BrowserAgent safety route" in review, "team review missing BrowserAgent safety route")
    assert_true("status/safety only" in review.lower(), "team review missing status/safety wording")

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
        "read_password",
        "password_manager",
    ]
    for token in forbidden:
        assert_true(token not in source_text, f"forbidden browser execution/privacy code found: {token}")

    print("verify_eva_browser_agent_safety: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
