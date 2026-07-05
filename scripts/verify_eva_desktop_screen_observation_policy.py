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
        "DesktopScreenObservationPolicy(",
        "DesktopScreenObservationPreview(",
        "DesktopScreenObservationSafetyDecision(",
        "DesktopScreenRedactionRule(",
        "DesktopScreenObservationReadiness(",
        "DesktopScreenCaptureGate(",
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


def assert_policy_text(text: str, label: str) -> None:
    assert_clean(text, label)
    lower = text.lower()
    assert_true("desktop" in lower or "screen" in lower, f"{label} missing desktop/screen wording")
    assert_true("locked" in lower or "blocked" in lower or "no app or window control" in lower, f"{label} missing locked/blocked wording")
    assert_true("policy" in lower or "readiness" in lower or "redaction" in lower or "gate" in lower or "sensitive" in lower, f"{label} missing policy/status wording")
    assert_true("no screen" in lower or "real screen observation: locked" in lower or "screen capture: locked" in lower or "no saved screenshots" in lower, f"{label} missing no-real-screen/persistent-capture boundary")


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
        format_desktop_observation_policy,
        format_desktop_screen_capture_gate,
        format_desktop_screen_observation_policy,
        format_desktop_screen_policy,
        format_desktop_screen_readiness,
        format_desktop_screen_redaction_policy,
        format_desktop_sensitive_screens,
    )
    from backend.eva.desktop_agent.redaction_policy import get_desktop_screen_redaction_rules
    from backend.eva.desktop_agent.screen_observation import create_screen_observation_preview, get_desktop_screen_capture_gate
    from backend.eva.desktop_agent.screen_policy import evaluate_screen_observation_safety, get_desktop_screen_policy, list_sensitive_screen_categories
    from backend.eva.planner.capability_selector import select_capabilities_for_goal
    from backend.eva.planner.decomposer import create_task_plan

    policy = get_desktop_screen_policy()
    assert_true(policy.real_screen_capture_allowed is False, "screen capture unexpectedly allowed")
    assert_true(policy.screenshots_allowed is False, "screenshots unexpectedly allowed")
    assert_true(policy.ocr_allowed is False, "OCR unexpectedly allowed")
    assert_true(policy.image_analysis_allowed is False, "image analysis unexpectedly allowed")

    categories = list_sensitive_screen_categories()
    assert_true("passwords_or_credentials" in [item.value for item in categories], "credential category missing")
    assert_true("browser_sessions" in [item.value for item in categories], "browser session category missing")

    redaction_rules = get_desktop_screen_redaction_rules()
    assert_true(any(rule.replacement == "[REDACTED_SECRET]" for rule in redaction_rules), "secret redaction rule missing")
    assert_true(any("password" in rule.name.lower() for rule in redaction_rules), "password redaction rule missing")

    gate = get_desktop_screen_capture_gate()
    assert_true(gate.status == "locked", "screen capture gate not locked")
    assert_true(gate.capture_allowed_now is False, "capture gate unexpectedly allows capture")

    preview = create_screen_observation_preview()
    assert_true(preview.mode == "policy_preview_only", "screen observation preview not policy-only")
    assert_true(preview.real_capture_performed is False, "screen observation preview performed capture")

    safety = evaluate_screen_observation_safety("take screenshot of my desktop")
    assert_true(safety.allowed_now is False, "screenshot observation unexpectedly allowed")
    assert_true(safety.decision in {"locked", "blocked"}, "screenshot decision not locked/blocked")

    outputs = {
        "screen policy": format_desktop_screen_policy(),
        "screen observation policy": format_desktop_screen_observation_policy(),
        "sensitive screens": format_desktop_sensitive_screens(),
        "screen redaction policy": format_desktop_screen_redaction_policy(),
        "screen capture gate": format_desktop_screen_capture_gate(),
        "screen readiness": format_desktop_screen_readiness(),
        "observation policy": format_desktop_observation_policy(),
    }
    for label, output in outputs.items():
        assert_policy_text(output, label)

    commands = [
        "eva desktop screen policy",
        "eva desktop screen observation policy",
        "eva desktop sensitive screens",
        "eva desktop screen redaction policy",
        "eva desktop screen capture gate",
        "eva desktop screen readiness",
        "eva desktop observation policy",
        "eva ask can Eva see my screen",
        "eva ask can Eva take screenshots",
        "eva ask can Eva read my screen",
        "eva ask what screens are sensitive",
        "eva ask show screen observation policy",
        "eva ask what would Eva redact from screen",
        "eva ask is screen observation ready",
    ]
    for command in commands:
        output = run_fast_command(command)
        assert_policy_text(output, command)

    routes = {
        "can Eva see my screen": "desktop_observe_policy",
        "can Eva take screenshots": "desktop_screen_capture_gate",
        "can Eva read my screen": "desktop_screen_policy",
        "what screens are sensitive": "desktop_sensitive_screens",
        "show screen observation policy": "desktop_screen_observation_policy",
        "what would Eva redact from screen": "desktop_screen_redaction_policy",
        "is screen observation ready": "desktop_screen_readiness",
    }
    for prompt, expected_intent in routes.items():
        route = route_natural_request(prompt)
        assert_true(route.intent == expected_intent, f"{prompt!r} routed to {route.intent}, expected {expected_intent}")
        assert_true(route.authority_category == "read", f"{prompt!r} is not policy/read")
        assert_true(route.real_execution_requested is False, f"{prompt!r} requested real screen execution")

    control = format_control_center_text()
    assert_clean(control, "control center")
    assert_true("Desktop Screen Observation Policy" in control, "Control Center missing Desktop Screen Observation Policy panel")
    assert_true("screen capture" in control.lower(), "Control Center missing screen capture wording")
    assert_true("redaction" in control.lower(), "Control Center missing redaction wording")
    assert_true("Keyboard/Mouse Action Dry-Run Schema" in control, "Control Center missing next phase")

    for capability_id in (
        "desktop.screen_policy",
        "desktop.screen_observation_policy",
        "desktop.sensitive_screens",
        "desktop.screen_redaction_policy",
        "desktop.screen_capture_gate",
        "desktop.screen_readiness",
        "desktop.observation_policy",
    ):
        assert_true(get_capability(capability_id) is not None, f"missing capability {capability_id}")
        permission = get_capability_permission(capability_id)
        assert_true(permission.read_only and not permission.external_effect, f"{capability_id} not read-only")
        assert_true(resolve_capability(capability_id).resource_id == "eva-desktop-agent-safety", f"missing resource for {capability_id}")
        assert_true(capability_to_tool_schema(capability_id) is not None, f"missing schema for {capability_id}")

    caps = select_capabilities_for_goal("show screen observation policy and what would Eva redact from screen")
    assert_true("desktop.screen_observation_policy" in caps, "planner selector missed desktop.screen_observation_policy")
    assert_true("desktop.screen_redaction_policy" in caps, "planner selector missed desktop.screen_redaction_policy")
    plan = create_task_plan("can Eva take screenshots")
    assert_true(any(step.capability_id == "desktop.screen_capture_gate" for step in plan.steps), "planner missing screen capture gate")
    assert_true(all(step.permission_status in {"allowed", "preview_only"} for step in plan.steps), "screen policy plan contains executable/risky permission")
    review = format_team_review("can Eva read my screen")
    assert_clean(review, "team review")
    assert_true("DesktopAgent screen observation policy route" in review, "team review missing screen observation route")
    assert_true("policy/status only" in review.lower(), "team review missing policy/status wording")

    for action in ("screen_capture", "screenshot", "app_launch", "mouse_click", "keyboard_type", "hotkey", "clipboard_read", "file_dialog", "terminal_shell"):
        decision = evaluate_desktop_action_safety(action)
        assert_true(not decision.allowed_now, f"{action} unexpectedly allowed after screen policy")

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
        "pytesseract",
        "easyocr",
        "cv2.",
        "screenshot(",
        "grab(",
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
        assert_true(token not in source_text, f"forbidden desktop screen execution/privacy code found: {token}")

    print("verify_eva_desktop_screen_observation_policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
