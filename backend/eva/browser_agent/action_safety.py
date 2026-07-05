from __future__ import annotations

from .models import BrowserActionCategory, BrowserActionSafetyDecision, BrowserBlockedAction


_ALIASES = {
    "status": BrowserActionCategory.READ_STATUS,
    "browser status": BrowserActionCategory.READ_STATUS,
    "observe": BrowserActionCategory.OBSERVE_PAGE_PREVIEW,
    "observe page": BrowserActionCategory.OBSERVE_PAGE_PREVIEW,
    "summarize": BrowserActionCategory.SUMMARIZE_PAGE_PREVIEW,
    "summarize page": BrowserActionCategory.SUMMARIZE_PAGE_PREVIEW,
    "navigate": BrowserActionCategory.NAVIGATE_PREVIEW,
    "open page": BrowserActionCategory.NAVIGATE_PREVIEW,
    "search": BrowserActionCategory.SEARCH_PREVIEW,
    "click": BrowserActionCategory.CLICK,
    "type": BrowserActionCategory.TYPE,
    "submit": BrowserActionCategory.SUBMIT,
    "login": BrowserActionCategory.LOGIN,
    "log in": BrowserActionCategory.LOGIN,
    "payment": BrowserActionCategory.PAYMENT,
    "pay": BrowserActionCategory.PAYMENT,
    "upload": BrowserActionCategory.FILE_UPLOAD,
    "file upload": BrowserActionCategory.FILE_UPLOAD,
    "download": BrowserActionCategory.DOWNLOAD,
    "cookies": BrowserActionCategory.COOKIE_ACCESS,
    "cookie": BrowserActionCategory.COOKIE_ACCESS,
    "cookie_access": BrowserActionCategory.COOKIE_ACCESS,
    "local storage": BrowserActionCategory.LOCAL_STORAGE_ACCESS,
    "localstorage": BrowserActionCategory.LOCAL_STORAGE_ACCESS,
    "local_storage_access": BrowserActionCategory.LOCAL_STORAGE_ACCESS,
    "profile": BrowserActionCategory.PROFILE_ACCESS,
    "profile_access": BrowserActionCategory.PROFILE_ACCESS,
    "send": BrowserActionCategory.EXTERNAL_SEND,
    "external_send": BrowserActionCategory.EXTERNAL_SEND,
}

_PREVIEW_ALLOWED = {
    BrowserActionCategory.READ_STATUS,
    BrowserActionCategory.OBSERVE_PAGE_PREVIEW,
    BrowserActionCategory.SUMMARIZE_PAGE_PREVIEW,
    BrowserActionCategory.NAVIGATE_PREVIEW,
    BrowserActionCategory.SEARCH_PREVIEW,
}

_BLOCK_REASONS = {
    BrowserActionCategory.CLICK: "Clicking is real browser control and is locked in Phase 13A.",
    BrowserActionCategory.TYPE: "Typing into pages is real browser control and is locked in Phase 13A.",
    BrowserActionCategory.SUBMIT: "Submitting forms can create external effects and is locked.",
    BrowserActionCategory.LOGIN: "Login automation and account workflows are locked.",
    BrowserActionCategory.PAYMENT: "Payment and purchase flows are hard-blocked for this foundation phase.",
    BrowserActionCategory.FILE_UPLOAD: "File uploads can expose local data and are locked.",
    BrowserActionCategory.DOWNLOAD: "Downloads are local file effects and are locked.",
    BrowserActionCategory.COOKIE_ACCESS: "Cookie access is forbidden; Eva must not read browser sessions.",
    BrowserActionCategory.LOCAL_STORAGE_ACCESS: "localStorage access is forbidden; Eva must not read browser sessions.",
    BrowserActionCategory.PROFILE_ACCESS: "Browser profile/session access is forbidden.",
    BrowserActionCategory.EXTERNAL_SEND: "External sends, posts, and form submissions require future confirmation-gated design and are locked now.",
    BrowserActionCategory.UNKNOWN: "Unknown browser actions are blocked by default.",
}


def normalize_browser_action(action: str) -> BrowserActionCategory:
    text = " ".join(str(action or "").strip().lower().replace("-", " ").split())
    if not text:
        return BrowserActionCategory.UNKNOWN
    if text in _ALIASES:
        return _ALIASES[text]
    for key, category in _ALIASES.items():
        if key in text:
            return category
    return BrowserActionCategory.UNKNOWN


def evaluate_browser_action_safety(action: str) -> BrowserActionSafetyDecision:
    category = normalize_browser_action(action)
    if category in _PREVIEW_ALLOWED:
        return BrowserActionSafetyDecision(
            action=str(action or "").strip() or category.value,
            category=category,
            decision="preview_only",
            allowed_now=True,
            reason="Allowed only as a status/policy preview. No browser is launched, navigated, observed, or controlled.",
            required_future_gate="Future BrowserAgent executor with visible user intent, domain policy, observation limits, and permission gates.",
            safe_alternative="Use `eva browser policy` or `eva browser readiness` for the current locked status.",
        )
    reason = _BLOCK_REASONS.get(category, _BLOCK_REASONS[BrowserActionCategory.UNKNOWN])
    return BrowserActionSafetyDecision(
        action=str(action or "").strip() or category.value,
        category=category,
        decision="blocked",
        allowed_now=False,
        reason=reason,
        required_future_gate="Future permission-gated BrowserAgent executor; not enabled in Phase 13A.",
        safe_alternative="Use `eva browser action safety <action>` for a preview, or keep the task manual.",
    )


def list_blocked_browser_actions() -> list[BrowserBlockedAction]:
    categories = [
        BrowserActionCategory.CLICK,
        BrowserActionCategory.TYPE,
        BrowserActionCategory.SUBMIT,
        BrowserActionCategory.LOGIN,
        BrowserActionCategory.PAYMENT,
        BrowserActionCategory.FILE_UPLOAD,
        BrowserActionCategory.DOWNLOAD,
        BrowserActionCategory.COOKIE_ACCESS,
        BrowserActionCategory.LOCAL_STORAGE_ACCESS,
        BrowserActionCategory.PROFILE_ACCESS,
        BrowserActionCategory.EXTERNAL_SEND,
        BrowserActionCategory.UNKNOWN,
    ]
    return [
        BrowserBlockedAction(
            action=category.value,
            category=category,
            reason=_BLOCK_REASONS.get(category, _BLOCK_REASONS[BrowserActionCategory.UNKNOWN]),
            future_gate="Future BrowserAgent executor with human-in-the-loop permission gates.",
        )
        for category in categories
    ]
