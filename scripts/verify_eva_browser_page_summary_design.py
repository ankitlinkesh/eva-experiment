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
        "BrowserPageSummaryPreview(",
        "BrowserTextSummaryPreview(",
        "BrowserDomSummaryPreview(",
        "BrowserObservationPolicy(",
        "BrowserObservationSafetyDecision(",
        "BrowserRedactionRule(",
        "BrowserExtractionPreview(",
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
    from backend.eva.browser_agent.formatter import (
        format_browser_dom_summary_policy,
        format_browser_observation_readiness,
        format_browser_page_summary_policy,
        format_browser_page_summary_preview,
        format_browser_redaction_policy,
        format_browser_text_extraction_policy,
    )
    from backend.eva.browser_agent.observation_policy import (
        evaluate_observation_safety,
        get_browser_observation_policy,
        get_browser_redaction_rules,
    )
    from backend.eva.browser_agent.page_summary import (
        create_extraction_preview,
        create_mock_page_summary_preview,
        create_mock_text_summary_preview,
        create_schema_dom_summary_preview,
    )
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    policy = get_browser_observation_policy()
    assert_true(policy.live_page_reads_allowed is False, "live page reads unexpectedly enabled")
    assert_true(policy.dom_reads_allowed is False, "DOM reads unexpectedly enabled")
    assert_true(policy.screenshots_allowed is False, "screenshots unexpectedly enabled")
    assert_true(policy.browser_launch_allowed is False, "browser launch unexpectedly enabled")

    page_preview = create_mock_page_summary_preview("Eva Test Page", "This is user-provided mock text for summary design only.")
    text_preview = create_mock_text_summary_preview("Heading\nUseful body text\nFooter")
    dom_preview = create_schema_dom_summary_preview()
    extraction = create_extraction_preview()
    assert_true(page_preview.source == "user_provided_mock_text", "page preview source is not mock text")
    assert_true(text_preview.live_page_read is False, "text preview performed live read")
    assert_true(dom_preview.live_dom_read is False, "DOM preview performed live read")
    assert_true(extraction.live_extraction_enabled is False, "live extraction unexpectedly enabled")

    rules = get_browser_redaction_rules()
    assert_true(any("cookie" in rule.name.lower() or "token" in rule.name.lower() for rule in rules), "redaction rules missing cookie/token coverage")

    for action in ("live_page_read", "dom_read", "screenshot", "browser_launch", "click", "type", "submit", "download", "cookie_access"):
        decision = evaluate_observation_safety(action)
        assert_true(decision.allowed_now is False, f"{action} unexpectedly allowed")
        assert_true(decision.decision in {"locked", "blocked"}, f"{action} not locked/blocked")

    for label, output in [
        ("page summary policy", format_browser_page_summary_policy()),
        ("page summary preview", format_browser_page_summary_preview()),
        ("dom summary policy", format_browser_dom_summary_policy()),
        ("text extraction policy", format_browser_text_extraction_policy()),
        ("observation readiness", format_browser_observation_readiness()),
        ("redaction policy", format_browser_redaction_policy()),
    ]:
        assert_clean(output, label)
        lower = output.lower()
        assert_true("browser" in lower, f"{label} missing browser wording")
        assert_true("locked" in lower or "blocked" in lower or "preview" in lower, f"{label} missing locked/preview wording")
        assert_true("live browser observation is locked" in lower or "no live" in lower or "execution:" in lower, f"{label} missing no-live-observation boundary")

    commands = [
        "eva browser page summary policy",
        "eva browser page summary preview",
        "eva browser dom summary policy",
        "eva browser text extraction policy",
        "eva browser observation readiness",
        "eva browser redaction policy",
        "eva ask can Eva read a webpage",
        "eva ask can Eva summarize a page",
        "eva ask can Eva inspect DOM",
        "eva ask can Eva take screenshots",
        "eva ask show browser observation policy",
        "eva ask what would Eva extract from a webpage",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        lower = output.lower()
        assert_true("browser" in lower or "webpage" in lower, f"{command} missing browser/webpage wording")
        assert_true("locked" in lower or "preview" in lower or "blocked" in lower or "read-only" in lower, f"{command} missing locked/preview/read-only boundary")

    routes = {
        "can Eva read a webpage": "browser_read_policy",
        "can Eva summarize a page": "browser_page_summary_policy",
        "can Eva inspect DOM": "browser_dom_summary_policy",
        "can Eva take browser screenshots": "browser_observation_readiness",
        "show browser observation policy": "browser_observation_readiness",
        "what would Eva extract from a webpage": "browser_page_summary_preview",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not read/status")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real browser observation")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Browser Observation Preview" in control, "Control Center missing Browser Observation Preview panel")
    assert_true("live browser reads locked" in control.lower() or "live reads" in control.lower(), "Control Center missing live-read lock")
    assert_true("redaction" in control.lower(), "Control Center missing redaction policy")

    for capability_id in (
        "browser.page_summary_policy",
        "browser.page_summary_preview",
        "browser.dom_summary_policy",
        "browser.text_extraction_policy",
        "browser.observation_readiness",
        "browser.redaction_policy",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-browser-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("can Eva summarize a page and inspect DOM")
    assert_true("browser.page_summary_policy" in caps, "planner selector missed page summary policy")
    assert_true("browser.dom_summary_policy" in caps, "planner selector missed DOM summary policy")
    plan = create_task_plan("what would Eva extract from a webpage")
    assert_true(any(step.capability_id == "browser.page_summary_preview" for step in plan.steps), "planner missing page summary preview")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in plan.steps), "page summary plan contains executable/risky permission")
    review = format_team_review("can Eva inspect DOM and summarize a page")
    assert_clean(review, "team review")
    assert_true("BrowserAgent observation preview route" in review, "team review missing observation preview route")
    assert_true("preview/status only" in review.lower(), "team review missing preview/status wording")

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
        "document.queryselector",
        "document.body",
        "innertext",
    ]
    for token in forbidden:
        assert_true(token not in source_text, f"forbidden browser execution/privacy code found: {token}")

    print("verify_eva_browser_page_summary_design: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
