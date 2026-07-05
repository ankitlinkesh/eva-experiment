from __future__ import annotations

from .action_plan import BrowserActionApprovalRequirement, BrowserActionDryRun, BrowserActionPlanPreview, BrowserActionStepPreview
from .risk import evaluate_browser_action_risk


BLOCKED_BROWSER_EXECUTION: tuple[str, ...] = (
    "actual browser launch or navigation",
    "live page reads, DOM access, screenshots, or screen capture",
    "clicking, typing, forms, login, payment, upload, or download",
    "cookie, localStorage, session, profile, password, or token reads",
    "Playwright, browser-use, Stagehand, Maxun, MCP, PyAutoGUI, desktop, shell, package, or cloud calls",
)


def create_browser_action_dry_run(request: str) -> BrowserActionDryRun:
    steps = _steps_for_request(request)
    return BrowserActionDryRun(
        request=_clean_request(request),
        execution_enabled=False,
        steps=steps,
        blocked_execution=BLOCKED_BROWSER_EXECUTION,
        summary="Browser action dry-run only. Real browser execution is locked.",
    )


def create_browser_action_plan_preview(request: str) -> BrowserActionPlanPreview:
    steps = _steps_for_request(request)
    return BrowserActionPlanPreview(
        request=_clean_request(request),
        mode="dry_run_only",
        real_browser_execution="locked",
        steps=steps,
        approvals=get_browser_action_approval_requirements(),
        next_phase="Future BrowserAgent executor gate with observation, confirmation, verification, and rollback/repair policy.",
    )


def get_browser_action_approval_requirements() -> tuple[BrowserActionApprovalRequirement, ...]:
    return (
        BrowserActionApprovalRequirement("navigate_preview", "future read-only domain and privacy gate", "not executable now"),
        BrowserActionApprovalRequirement("search_preview", "future read-only domain and privacy gate", "not executable now"),
        BrowserActionApprovalRequirement("extract_preview", "future observation/redaction approval", "not executable now"),
        BrowserActionApprovalRequirement("screenshot_preview", "future explicit screenshot permission", "not executable now"),
        BrowserActionApprovalRequirement("click_preview", "future exact user confirmation", "blocked now"),
        BrowserActionApprovalRequirement("type_preview", "future exact user confirmation with field verification", "blocked now"),
        BrowserActionApprovalRequirement("submit_preview", "future external-action confirmation", "blocked now"),
        BrowserActionApprovalRequirement("login_preview", "future hard refusal or explicit private workflow gate", "blocked now"),
        BrowserActionApprovalRequirement("upload_preview", "future file/privacy confirmation", "blocked now"),
        BrowserActionApprovalRequirement("download_preview", "future download/path safety gate", "blocked now"),
    )


def _steps_for_request(request: str) -> tuple[BrowserActionStepPreview, ...]:
    text = str(request or "").lower()
    actions: list[str] = []
    if any(term in text for term in ("open", "website", "site", "url", ".com", "http")):
        actions.append("navigate")
    if "search" in text or "google" in text:
        actions.append("search")
    if "click" in text:
        actions.append("click")
    if "type" in text or "fill" in text:
        actions.append("type")
    if "submit" in text or "form" in text:
        actions.append("submit")
    if "login" in text or "log in" in text or "sign in" in text:
        actions.append("login")
    if "upload" in text:
        actions.append("upload")
    if "download" in text:
        actions.append("download")
    if "extract" in text or "summary" in text or "summarize" in text:
        actions.append("extract")
    if "screenshot" in text:
        actions.append("screenshot")
    if not actions:
        actions.append("unknown")
    return tuple(_step(index, action) for index, action in enumerate(actions, start=1))


def _step(index: int, action: str) -> BrowserActionStepPreview:
    risk = evaluate_browser_action_risk(action)
    return BrowserActionStepPreview(
        step_id=f"browser-dry-run-{index}",
        action_type=risk.action_type,
        description=f"Preview {risk.action_type.replace('_', ' ')} for the request.",
        risk=risk,
        would_execute_now=False,
        blocked_reason="Real browser execution is locked in Phase 13D.",
        required_approval=risk.approval_required,
    )


def _clean_request(request: str) -> str:
    text = " ".join(str(request or "").split())
    return text[:160] if text else "browser action dry run"
