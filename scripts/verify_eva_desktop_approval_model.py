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
        "DesktopApprovalPolicy(",
        "DesktopApprovalRequestPreview(",
        "DesktopApprovalDecisionPreview(",
        "DesktopApprovalAuditRecord(",
        "DesktopApprovalExpiration(",
        "DesktopConfirmationPhrase(",
        "DesktopApprovalReadiness(",
        "DesktopForbiddenActionClass(",
        "DesktopApprovalGateResult(",
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
    from backend.eva.desktop_agent.approval_audit import get_desktop_approval_audit_status
    from backend.eva.desktop_agent.approval_model import DesktopApprovalLevel, DesktopApprovalState, preview_desktop_approval_request
    from backend.eva.desktop_agent.approval_policy import get_desktop_approval_policy, list_desktop_forbidden_action_classes
    from backend.eva.desktop_agent.confirmation_phrases import preview_desktop_confirmation_phrase
    from backend.eva.desktop_agent.formatter import (
        format_desktop_approval_audit_status,
        format_desktop_approval_levels,
        format_desktop_approval_model_readiness,
        format_desktop_approval_model_preview,
        format_desktop_approval_policy,
        format_desktop_confirmation_phrase,
        format_desktop_forbidden_actions,
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

    policy = get_desktop_approval_policy()
    assert_true(policy.real_execution_unlocked is False, "approval policy unexpectedly unlocks real execution")
    assert_true("forbidden_no_approval_available" in [level.value for level in policy.approval_levels], "forbidden approval level missing")
    assert_true(list_desktop_forbidden_action_classes(), "forbidden action classes missing")

    audit = get_desktop_approval_audit_status()
    assert_true(audit.status == "schema/status only", "approval audit is not schema/status only")
    assert_true(audit.records_count == 0, "approval audit should not create real records")

    risky_requests = {
        "click save": {DesktopApprovalLevel.EXPLICIT_CONFIRMATION_REQUIRED, DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED},
        "type my password": {DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE, DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED},
        "send a message": {DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE},
        "open terminal": {DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE},
        "delete a file": {DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE},
        "change system settings": {DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE},
        "unknown screen context": {DesktopApprovalLevel.ELEVATED_CONFIRMATION_REQUIRED, DesktopApprovalLevel.FORBIDDEN_NO_APPROVAL_AVAILABLE},
    }
    for request, allowed_levels in risky_requests.items():
        preview = preview_desktop_approval_request(request)
        assert_true(preview.decision.execution_unlocked is False, f"{request} unexpectedly unlocks execution")
        assert_true(preview.decision.approval_level in allowed_levels, f"{request} approval level too low: {preview.decision.approval_level}")
        assert_true(preview.decision.state in {DesktopApprovalState.PENDING_FUTURE_APPROVAL, DesktopApprovalState.BLOCKED, DesktopApprovalState.FORBIDDEN}, f"{request} state unexpected")

    phrase = preview_desktop_confirmation_phrase("send a message")
    assert_true(phrase.phrase_type.value in {"elevated_sensitive_action_confirmation", "forbidden_action_refusal"}, "message phrase type too weak")
    assert_true(phrase.unlocks_execution is False, "confirmation phrase unexpectedly unlocks execution")

    for label, output in [
        ("policy", format_desktop_approval_policy()),
        ("levels", format_desktop_approval_levels()),
        ("preview", format_desktop_approval_model_preview("click save")),
        ("password preview", format_desktop_approval_model_preview("type my password")),
        ("phrase", format_desktop_confirmation_phrase("send a message")),
        ("forbidden", format_desktop_forbidden_actions()),
        ("audit", format_desktop_approval_audit_status()),
        ("readiness", format_desktop_approval_model_readiness()),
    ]:
        assert_clean(output, label)
        lower = output.lower()
        assert_true("desktop" in lower, f"{label} missing desktop wording")
        assert_true("approval" in lower or "confirmation" in lower or "forbidden" in lower, f"{label} missing approval wording")
        assert_true("locked" in lower or "does not unlock" in lower or "execution:" in lower, f"{label} missing locked execution wording")

    commands = [
        "eva desktop approval policy",
        "eva desktop approval levels",
        "eva desktop approval preview click save",
        "eva desktop approval preview type my password",
        "eva desktop confirmation phrase send a message",
        "eva desktop forbidden actions",
        "eva desktop approval audit status",
        "eva desktop approval readiness",
        "eva ask what approval is needed to click",
        "eva ask can I approve Eva to control my desktop",
        "eva ask what desktop actions are forbidden",
        "eva ask what confirmation phrase would be required",
        "eva ask is desktop approval ready",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_clean(output, command)
        lower = output.lower()
        assert_true("desktop" in lower, f"{command} missing desktop wording")
        assert_true("locked" in lower or "approval" in lower or "confirmation" in lower or "forbidden" in lower, f"{command} missing approval/locked boundary")
        assert_true("unlock real desktop execution" not in lower or "does not unlock real desktop execution" in lower, f"{command} suggests approval unlocks execution")

    routes = {
        "what approval is needed to click": "desktop_approval_preview",
        "what approval is needed to type my password": "desktop_approval_preview",
        "can I approve Eva to control my desktop": "desktop_approval_policy",
        "show desktop approval policy": "desktop_approval_policy",
        "what desktop actions are forbidden": "desktop_forbidden_actions",
        "what confirmation phrase would be required": "desktop_confirmation_phrase",
        "is desktop approval ready": "desktop_approval_readiness",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not read/status")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real desktop execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Desktop Human Approval Model" in control, "Control Center missing Desktop Human Approval Model panel")
    assert_true("approval levels" in control.lower(), "Control Center missing approval levels")
    assert_true("confirmation phrase" in control.lower(), "Control Center missing confirmation phrase policy")
    assert_true("does not unlock" in control.lower() or "locked" in control.lower(), "Control Center missing non-unlock boundary")

    for capability_id in (
        "desktop.approval_policy",
        "desktop.approval_levels",
        "desktop.approval_preview",
        "desktop.confirmation_phrase",
        "desktop.forbidden_actions",
        "desktop.approval_audit_status",
        "desktop.approval_readiness",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-desktop-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("show desktop approval policy and what confirmation phrase would be required")
    assert_true("desktop.approval_policy" in caps, "planner selector missed desktop.approval_policy")
    assert_true("desktop.confirmation_phrase" in caps, "planner selector missed desktop.confirmation_phrase")
    task_plan = create_task_plan("what approval is needed to click")
    assert_true(any(step.capability_id == "desktop.approval_preview" for step in task_plan.steps), "planner missing desktop approval preview")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in task_plan.steps), "desktop approval plan contains executable/risky permission")
    review = format_team_review("what approval is needed to type my password")
    assert_clean(review, "team review")
    assert_true("DesktopAgent human approval route" in review, "team review missing human approval route")
    assert_true("approval-policy/status only" in review.lower(), "team review missing approval-policy/status wording")

    docs = [
        ROOT / "docs" / "EVA_CURRENT_STATE.md",
        ROOT / "docs" / "EVA_CAPABILITIES.md",
        ROOT / "docs" / "EVA_AGENT_FRAMEWORK.md",
        ROOT / "docs" / "EVA_THREAT_MODEL.md",
        ROOT / "docs" / "EVA_VERIFICATION.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        assert_true("Desktop Human Approval Model" in text or "human approval model" in text.lower(), f"{doc.name} missing desktop approval model docs")
    current_state = (ROOT / "docs" / "EVA_CURRENT_STATE.md").read_text(encoding="utf-8")
    for expected in ("Phase 14G", "Phase 15 LLM Router", "Phase 16 Context Assembly", "Phase 17 LLM Threat Defense", "Phase 18 Agent Loop"):
        assert_true(expected in current_state, f"roadmap missing {expected}")

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

    print("verify_eva_desktop_approval_model: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
