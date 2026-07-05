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
        "BrowserActionDryRun(",
        "BrowserActionStepPreview(",
        "BrowserActionRisk(",
        "BrowserActionDryRunResult(",
        "BrowserActionPlanPreview(",
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
    from backend.eva.browser_agent.action_dry_run import create_browser_action_dry_run, create_browser_action_plan_preview
    from backend.eva.browser_agent.formatter import (
        format_browser_action_approvals,
        format_browser_action_dry_run,
        format_browser_action_plan,
        format_browser_action_readiness,
        format_browser_action_risk,
        format_browser_dry_run_policy,
    )
    from backend.eva.browser_agent.risk import BrowserActionRiskLevel, evaluate_browser_action_risk
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    dry_run = create_browser_action_dry_run("open example.com and click login")
    assert_true(dry_run.execution_enabled is False, "dry-run unexpectedly enables execution")
    assert_true(any(step.action_type == "navigate_preview" for step in dry_run.steps), "dry-run missing navigate preview")
    assert_true(any(step.action_type == "click_preview" for step in dry_run.steps), "dry-run missing click preview")

    plan = create_browser_action_plan_preview("search for drone motors")
    assert_true(plan.mode == "dry_run_only", "plan preview mode is not dry-run only")
    assert_true(plan.real_browser_execution == "locked", "plan preview does not lock browser execution")

    critical_actions = ("click", "type", "submit", "login", "payment", "upload", "download")
    for action in critical_actions:
        risk = evaluate_browser_action_risk(action)
        assert_true(risk.level in {BrowserActionRiskLevel.CRITICAL_BLOCKED, BrowserActionRiskLevel.FORBIDDEN}, f"{action} was not critical/forbidden")
        assert_true(risk.executable_now is False, f"{action} unexpectedly executable")

    preview_actions = ("navigate", "search", "extract", "screenshot")
    for action in preview_actions:
        risk = evaluate_browser_action_risk(action)
        assert_true(risk.executable_now is False, f"{action} unexpectedly executable")
        assert_true("preview" in risk.action_type, f"{action} missing preview action type")

    for label, output in [
        ("dry run", format_browser_action_dry_run("open example.com")),
        ("action plan", format_browser_action_plan("search for drone motors")),
        ("risk", format_browser_action_risk("click")),
        ("approvals", format_browser_action_approvals()),
        ("policy", format_browser_dry_run_policy()),
        ("readiness", format_browser_action_readiness()),
    ]:
        assert_clean(output, label)
        lower = output.lower()
        assert_true("browser" in lower, f"{label} missing browser wording")
        assert_true("dry-run" in lower or "dry run" in lower or "risk" in lower or "approval" in lower, f"{label} missing dry-run/risk wording")
        assert_true("real browser execution is locked" in lower or "execution:" in lower or "locked" in lower, f"{label} missing execution lock")

    commands = [
        "eva browser action dry run open example.com",
        "eva browser action plan search for drone motors",
        "eva browser action risk click",
        "eva browser action approvals",
        "eva browser dry run policy",
        "eva browser action readiness",
        "eva ask dry run opening a website",
        "eva ask what would Eva do to search Google",
        "eva ask can Eva click this in browser",
        "eva ask can Eva type into a website",
        "eva ask plan browser actions for logging in",
        "eva ask what browser actions need approval",
        "eva ask show browser action dry run policy",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        lower = output.lower()
        assert_true("browser" in lower, f"{command} missing browser wording")
        assert_true("locked" in lower or "dry-run" in lower or "dry run" in lower or "blocked" in lower, f"{command} missing dry-run/locked boundary")

    routes = {
        "dry run opening a website": "browser_action_dry_run",
        "what would Eva do to search Google": "browser_action_plan_preview",
        "can Eva click this in browser": "browser_action_risk",
        "can Eva type into a website": "browser_action_risk",
        "plan browser actions for logging in": "browser_action_plan_preview",
        "what browser actions need approval": "browser_action_approvals",
        "show browser action dry run policy": "browser_dry_run_policy",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not read/status")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real browser execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Browser Action Dry-Run" in control, "Control Center missing Browser Action Dry-Run panel")
    assert_true("risk levels" in control.lower(), "Control Center missing risk levels")
    assert_true("approval" in control.lower(), "Control Center missing approval requirements")

    for capability_id in (
        "browser.action_dry_run",
        "browser.action_plan_preview",
        "browser.action_risk",
        "browser.action_approvals",
        "browser.dry_run_policy",
        "browser.action_readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-browser-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("dry run opening a website and can Eva click this in browser")
    assert_true("browser.action_dry_run" in caps, "planner selector missed browser.action_dry_run")
    assert_true("browser.action_risk" in caps, "planner selector missed browser.action_risk")
    task_plan = create_task_plan("plan browser actions for logging in")
    assert_true(any(step.capability_id == "browser.action_plan_preview" for step in task_plan.steps), "planner missing browser action plan preview")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in task_plan.steps), "browser dry-run plan contains executable/risky permission")
    review = format_team_review("plan browser actions for logging in")
    assert_clean(review, "team review")
    assert_true("BrowserAgent action dry-run route" in review, "team review missing action dry-run route")
    assert_true("dry-run/status only" in review.lower(), "team review missing dry-run/status wording")

    current_state = (ROOT / "docs" / "EVA_CURRENT_STATE.md").read_text(encoding="utf-8")
    for expected in (
        "13 BrowserAgent safety",
        "14 DesktopAgent safety",
        "15 Agentic Workflow Planner",
        "23 News/Web Intelligence Dashboard",
        "24 Coding Specialist/CodingAgent",
    ):
        assert_true(expected in current_state, f"roadmap missing {expected}")

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

    print("verify_eva_browser_action_dry_run: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
