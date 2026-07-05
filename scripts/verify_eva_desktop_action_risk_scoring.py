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
        "DesktopRiskScore(",
        "DesktopRiskFactor(",
        "DesktopRiskScoreResult(",
        "DesktopRiskMatrix(",
        "DesktopApprovalRequirement(",
        "DesktopSafetyMatrixDecision(",
        "DesktopRiskContext(",
        "Traceback",
        "C:\\Users\\",
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
    from backend.eva.desktop_agent.approval_requirements import DesktopApprovalLevel, determine_desktop_approval_requirement
    from backend.eva.desktop_agent.formatter import (
        format_desktop_approval_required,
        format_desktop_high_risk_actions,
        format_desktop_risk_factors,
        format_desktop_risk_readiness,
        format_desktop_risk_score,
        format_desktop_safety_matrix,
    )
    from backend.eva.desktop_agent.risk_scoring import DesktopRiskLevel, score_desktop_action_risk
    from backend.eva.desktop_agent.safety_matrix import build_desktop_safety_matrix
    from backend.eva.capabilities.permissions import get_capability_permission
    from backend.eva.capabilities.registry import get_capability
    from backend.eva.capabilities.resource_mapping import resolve_capability
    from backend.eva.capabilities.tool_schemas import capability_to_tool_schema
    from backend.eva.control_center.status import format_control_center_text
    from backend.eva.core.natural_router import route_natural_request
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan
    from backend.eva.agents.team_review import format_team_review

    matrix = build_desktop_safety_matrix()
    assert_true(matrix.decisions, "safety matrix is empty")
    assert_true(any(item.action_type == "terminal_preview" for item in matrix.decisions), "safety matrix missing terminal decision")

    high_or_critical = {DesktopRiskLevel.HIGH_APPROVAL_REQUIRED, DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, DesktopRiskLevel.FORBIDDEN_LOCKED}
    for request in ("click save", "type into an app", "press hotkey", "clipboard write"):
        result = score_desktop_action_risk(request)
        assert_true(result.score.level in high_or_critical, f"{request} was not high/critical")
        assert_true(result.execution_enabled is False, f"{request} unexpectedly enables execution")

    for request in ("open terminal", "install package", "change system settings"):
        result = score_desktop_action_risk(request)
        assert_true(result.score.level in {DesktopRiskLevel.CRITICAL_EXPLICIT_CONFIRMATION_REQUIRED, DesktopRiskLevel.FORBIDDEN_LOCKED}, f"{request} was not critical/forbidden")
        assert_true(result.approval.level in {DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE}, f"{request} approval level too low")

    for request in ("type my password", "paste secret token", "pay with card", "send a message", "upload a file"):
        result = score_desktop_action_risk(request)
        assert_true(result.score.level in high_or_critical, f"{request} was not high risk")
        assert_true(result.factors, f"{request} missing risk factors")

    for label, output in [
        ("score", format_desktop_risk_score("click save")),
        ("score password", format_desktop_risk_score("type my password")),
        ("factors", format_desktop_risk_factors("upload a file")),
        ("approval", format_desktop_approval_required("send a message")),
        ("matrix", format_desktop_safety_matrix()),
        ("high risk", format_desktop_high_risk_actions()),
        ("readiness", format_desktop_risk_readiness()),
    ]:
        assert_clean(output, label)
        lower = output.lower()
        assert_true("desktop" in lower, f"{label} missing desktop wording")
        assert_true("risk" in lower or "approval" in lower or "matrix" in lower, f"{label} missing risk/approval wording")
        assert_true("locked" in lower or "execution:" in lower, f"{label} missing locked execution wording")

    commands = [
        "eva desktop risk score click save",
        "eva desktop risk score type my password",
        "eva desktop risk factors upload a file",
        "eva desktop approval required send a message",
        "eva desktop safety matrix",
        "eva desktop high risk actions",
        "eva desktop risk readiness",
        "eva ask how risky is typing my password",
        "eva ask what approval is needed to send a message",
        "eva ask what desktop actions are high risk",
        "eva ask show desktop safety matrix",
        "eva ask score the risk of opening terminal",
        "eva ask score the risk of uploading a file",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        lower = output.lower()
        assert_true("desktop" in lower, f"{command} missing desktop wording")
        assert_true("locked" in lower or "risk" in lower or "approval" in lower, f"{command} missing risk/locked boundary")

    routes = {
        "how risky is clicking this": "desktop_risk_score",
        "how risky is typing my password": "desktop_risk_score",
        "what approval is needed to send a message": "desktop_approval_required",
        "what desktop actions are high risk": "desktop_high_risk_actions",
        "show desktop safety matrix": "desktop_safety_matrix",
        "score the risk of opening terminal": "desktop_risk_score",
        "score the risk of uploading a file": "desktop_risk_score",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not read/status")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real desktop execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Desktop Action Risk Scoring" in control, "Control Center missing Desktop Action Risk Scoring panel")
    assert_true("approval levels" in control.lower(), "Control Center missing approval levels")
    assert_true("forbidden" in control.lower(), "Control Center missing forbidden action classes")

    for capability_id in (
        "desktop.risk_score",
        "desktop.risk_factors",
        "desktop.approval_required",
        "desktop.safety_matrix",
        "desktop.high_risk_actions",
        "desktop.risk_readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-desktop-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("score the risk of opening terminal and show desktop safety matrix")
    assert_true("desktop.risk_score" in caps, "planner selector missed desktop.risk_score")
    assert_true("desktop.safety_matrix" in caps, "planner selector missed desktop.safety_matrix")
    task_plan = create_task_plan("what approval is needed to send a message")
    assert_true(any(step.capability_id == "desktop.approval_required" for step in task_plan.steps), "planner missing desktop approval required")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in task_plan.steps), "desktop risk plan contains executable/risky permission")
    review = format_team_review("score the risk of uploading a file")
    assert_clean(review, "team review")
    assert_true("DesktopAgent risk scoring route" in review, "team review missing desktop risk scoring route")
    assert_true("risk/status only" in review.lower(), "team review missing risk/status wording")

    docs = [
        ROOT / "docs" / "EVA_CURRENT_STATE.md",
        ROOT / "docs" / "EVA_CAPABILITIES.md",
        ROOT / "docs" / "EVA_AGENT_FRAMEWORK.md",
        ROOT / "docs" / "EVA_THREAT_MODEL.md",
        ROOT / "docs" / "EVA_VERIFICATION.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        assert_true("Desktop Action Risk Scoring" in text or "desktop action risk scoring" in text.lower(), f"{doc.name} missing desktop risk scoring docs")

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

    print("verify_eva_desktop_action_risk_scoring: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
