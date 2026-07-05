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
        "BrowserSiteRisk(",
        "BrowserDomainRule(",
        "BrowserDomainDecision(",
        "BrowserDomainPolicyResult(",
        "BrowserSensitiveActionMarker(",
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
    from backend.eva.browser_agent.domain_rules import evaluate_domain_policy, get_domain_rules, get_sensitive_action_markers
    from backend.eva.browser_agent.formatter import (
        format_browser_domain_approvals,
        format_browser_domain_check,
        format_browser_domain_readiness,
        format_browser_domain_rules,
        format_browser_sensitive_sites,
        format_browser_site_risk,
    )
    from backend.eva.browser_agent.site_risk import BrowserSiteRiskLevel, classify_site_risk
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    assert_true(get_domain_rules(), "domain rules missing")
    assert_true(get_sensitive_action_markers(), "sensitive action markers missing")

    low = classify_site_risk("example.com")
    docs = classify_site_risk("docs.python.org")
    search = classify_site_risk("google.com")
    assert_true(low.level in {BrowserSiteRiskLevel.SAFE_STATIC, BrowserSiteRiskLevel.NORMAL_WEB}, "example.com should be low/normal risk")
    assert_true(docs.category.value == "documentation", "docs.python.org should be documentation")
    assert_true(search.category.value == "search", "google.com should be search")

    for domain in ("gmail.com", "paypal.com", "bankofamerica.com", "drive.google.com", "facebook.com", "dropbox.com"):
        risk = classify_site_risk(domain)
        assert_true(risk.level not in {BrowserSiteRiskLevel.SAFE_STATIC, BrowserSiteRiskLevel.NORMAL_WEB}, f"{domain} not sensitive/high risk")

    harmful = classify_site_risk("malware.example")
    unknown = classify_site_risk("unknown-private-login.test")
    assert_true(harmful.level in {BrowserSiteRiskLevel.BLOCKED, BrowserSiteRiskLevel.UNKNOWN_HIGH_RISK}, "harmful domain not blocked/high risk")
    assert_true(unknown.level in {BrowserSiteRiskLevel.SENSITIVE_LOGIN, BrowserSiteRiskLevel.UNKNOWN_HIGH_RISK, BrowserSiteRiskLevel.BLOCKED}, "unknown private domain not high risk")

    decision = evaluate_domain_policy("https://gmail.com/mail")
    assert_true(decision.real_browser_access == "locked", "domain decision unexpectedly allows browser access")
    assert_true(decision.allowed_now is False, "domain decision unexpectedly allowed now")

    for label, output in [
        ("domain check", format_browser_domain_check("example.com")),
        ("site risk", format_browser_site_risk("gmail.com")),
        ("payment risk", format_browser_site_risk("paypal.com")),
        ("rules", format_browser_domain_rules()),
        ("sensitive", format_browser_sensitive_sites()),
        ("approvals", format_browser_domain_approvals()),
        ("readiness", format_browser_domain_readiness()),
    ]:
        assert_clean(output, label)
        lower = output.lower()
        assert_true("browser" in lower or "domain" in lower or "site" in lower, f"{label} missing domain/site wording")
        assert_true("locked" in lower or "risk" in lower or "approval" in lower or "policy" in lower, f"{label} missing policy/risk wording")
        assert_true("no network" in lower or "real browser access is locked" in lower or "execution:" in lower, f"{label} missing no-network/browser boundary")

    commands = [
        "eva browser domain check example.com",
        "eva browser site risk gmail.com",
        "eva browser site risk paypal.com",
        "eva browser domain rules",
        "eva browser sensitive sites",
        "eva browser domain approvals",
        "eva browser domain readiness",
        "eva ask is example.com safe for Eva",
        "eva ask can Eva open a banking website",
        "eva ask can Eva use Gmail",
        "eva ask can Eva upload files to a site",
        "eva ask what sites are risky",
        "eva ask show browser domain policy",
        "eva ask what approvals are needed for sensitive sites",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        lower = output.lower()
        assert_true("browser" in lower or "domain" in lower or "site" in lower, f"{command} missing domain/site wording")
        assert_true("locked" in lower or "risk" in lower or "approval" in lower or "blocked" in lower, f"{command} missing locked/risk boundary")

    routes = {
        "is example.com safe for Eva": "browser_domain_check",
        "can Eva open a banking website": "browser_site_risk",
        "can Eva use Gmail": "browser_site_risk",
        "can Eva upload files to a site": "browser_site_risk",
        "what sites are risky": "browser_sensitive_sites",
        "show browser domain policy": "browser_domain_rules",
        "what approvals are needed for sensitive sites": "browser_domain_approvals",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not read/status")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real browser/network execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Browser Domain Risk" in control, "Control Center missing Browser Domain Risk panel")
    assert_true("sensitive categories" in control.lower(), "Control Center missing sensitive categories")
    assert_true("approval" in control.lower(), "Control Center missing approval requirements")

    for capability_id in (
        "browser.domain_check",
        "browser.site_risk",
        "browser.domain_rules",
        "browser.sensitive_sites",
        "browser.domain_approvals",
        "browser.domain_readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-browser-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("is example.com safe for Eva and can Eva use Gmail")
    assert_true("browser.domain_check" in caps, "planner selector missed domain check")
    assert_true("browser.site_risk" in caps, "planner selector missed site risk")
    plan = create_task_plan("what approvals are needed for sensitive sites")
    assert_true(any(step.capability_id == "browser.domain_approvals" for step in plan.steps), "planner missing domain approvals")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in plan.steps), "domain plan contains executable/risky permission")
    review = format_team_review("can Eva use Gmail and upload files to a site")
    assert_clean(review, "team review")
    assert_true("BrowserAgent domain risk route" in review, "team review missing domain risk route")
    assert_true("policy/status only" in review.lower(), "team review missing policy/status wording")

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
        "import socket",
        "socket.",
        "gethostbyname",
        "dns.resolver",
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
        "urllib.request",
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
        assert_true(token not in source_text, f"forbidden browser/network execution/privacy code found: {token}")

    print("verify_eva_browser_domain_policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
