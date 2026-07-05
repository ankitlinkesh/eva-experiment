from __future__ import annotations

from .action_plan import (
    DesktopActionApprovalRequirement,
    DesktopActionDryRun,
    DesktopActionDryRunResult,
    DesktopActionPlanPreview,
    DesktopActionStepPreview,
    DesktopActionTargetPreview,
)
from .risk import evaluate_desktop_action_risk


BLOCKED_DESKTOP_ACTION_EXECUTION: tuple[str, ...] = (
    "real mouse movement, click, double-click, drag, or coordinate targeting",
    "real keyboard typing, hotkeys, shortcuts, or key presses",
    "clipboard reads or writes",
    "app launch, app focus, window inspection, or file dialog automation",
    "screen capture, screenshots, OCR, image analysis, or always-on watching",
    "terminal, shell, package, PyAutoGUI, Playwright, MCP, browser, desktop, network, or cloud calls",
)


def create_desktop_action_dry_run(request: str) -> DesktopActionDryRun:
    steps = _steps_for_request(request)
    return DesktopActionDryRun(
        request=_clean_request(request),
        execution_enabled=False,
        steps=steps,
        blocked_execution=BLOCKED_DESKTOP_ACTION_EXECUTION,
        summary="Desktop action dry-run only. Real desktop control is locked.",
    )


def create_desktop_action_plan_preview(request: str) -> DesktopActionPlanPreview:
    steps = _steps_for_request(request)
    return DesktopActionPlanPreview(
        request=_clean_request(request),
        mode="dry_run_only",
        real_desktop_execution="locked",
        steps=steps,
        approvals=get_desktop_action_approval_requirements(),
        next_phase="Future DesktopAgent action risk scoring with explicit permission, verified UI targets, audit, and rollback/repair policy.",
    )


def create_desktop_action_dry_run_result(request: str) -> DesktopActionDryRunResult:
    return DesktopActionDryRunResult(
        dry_run=create_desktop_action_dry_run(request),
        plan=create_desktop_action_plan_preview(request),
        status="preview_only",
        executed=False,
        ready_for_real_control=False,
    )


def get_desktop_action_approval_requirements() -> tuple[DesktopActionApprovalRequirement, ...]:
    return (
        DesktopActionApprovalRequirement("mouse_move_preview", "future verified UI target and explicit user-commanded task", "blocked now"),
        DesktopActionApprovalRequirement("mouse_click_preview", "future high-confidence target, confirmation when risky, and post-action verification", "blocked now"),
        DesktopActionApprovalRequirement("mouse_drag_preview", "future precise target bounds, confirmation, and rollback/repair plan", "blocked now"),
        DesktopActionApprovalRequirement("keyboard_type_preview", "future focused-field verification and external-send guard", "blocked now"),
        DesktopActionApprovalRequirement("hotkey_preview", "future app context, bounded allowlist, and confirmation for risky shortcuts", "blocked now"),
        DesktopActionApprovalRequirement("clipboard_read_preview", "future privacy gate", "blocked now"),
        DesktopActionApprovalRequirement("clipboard_write_preview", "future confirmation and clear audit trail", "blocked now"),
        DesktopActionApprovalRequirement("app_launch_preview", "future app-risk policy and user-commanded task gate", "blocked now"),
        DesktopActionApprovalRequirement("file_dialog_preview", "future path confinement and file privacy gate", "blocked now"),
        DesktopActionApprovalRequirement("screen_observation_preview", "future explicit screen observation permission and redaction policy", "blocked now"),
        DesktopActionApprovalRequirement("terminal_preview", "forbidden for DesktopAgent action dry-run", "not overridable now"),
    )


def _steps_for_request(request: str) -> tuple[DesktopActionStepPreview, ...]:
    text = str(request or "").lower()
    actions: list[str] = []
    if "drag" in text:
        actions.append("mouse drag")
    if "click" in text or "button" in text:
        actions.append("mouse click")
    if "move" in text and "mouse" in text:
        actions.append("mouse move")
    if "type" in text or "write into" in text or "enter text" in text:
        actions.append("keyboard type")
    if "hotkey" in text or "shortcut" in text or "ctrl" in text or "press" in text:
        actions.append("hotkey")
    if "clipboard" in text and any(term in text for term in ("read", "paste", "get")):
        actions.append("clipboard read")
    if "clipboard" in text and any(term in text for term in ("write", "copy", "set")):
        actions.append("clipboard write")
    if "open app" in text or "launch app" in text or "open an app" in text or "start app" in text:
        actions.append("app launch")
    if "file dialog" in text or "save dialog" in text or "open dialog" in text:
        actions.append("file dialog")
    if "terminal" in text or "shell" in text or "command" in text:
        actions.append("terminal")
    if "screen" in text or "screenshot" in text or "observe" in text:
        actions.append("screen observation")
    if not actions:
        actions.append("unknown")
    return tuple(_step(index, action) for index, action in enumerate(actions, start=1))


def _step(index: int, action: str) -> DesktopActionStepPreview:
    risk = evaluate_desktop_action_risk(action)
    return DesktopActionStepPreview(
        step_id=f"desktop-dry-run-{index}",
        action_type=risk.action_type,
        description=f"Preview {risk.action_type.replace('_', ' ')} for the request.",
        target=DesktopActionTargetPreview(
            label="unresolved preview target",
            target_type="text_only_preview",
            confidence="none",
            notes="No live screen, window, app, or coordinate target was inspected.",
        ),
        risk=risk,
        would_execute_now=False,
        blocked_reason="Real desktop control is locked in Phase 14D.",
        required_approval=risk.approval_required,
    )


def _clean_request(request: str) -> str:
    text = " ".join(str(request or "").split())
    return text[:160] if text else "desktop action dry run"
