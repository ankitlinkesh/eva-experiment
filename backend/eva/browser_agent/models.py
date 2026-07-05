from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum


class BrowserActionCategory(StrEnum):
    READ_STATUS = "read_status"
    OBSERVE_PAGE_PREVIEW = "observe_page_preview"
    SUMMARIZE_PAGE_PREVIEW = "summarize_page_preview"
    NAVIGATE_PREVIEW = "navigate_preview"
    SEARCH_PREVIEW = "search_preview"
    CLICK = "click"
    TYPE = "type"
    SUBMIT = "submit"
    LOGIN = "login"
    PAYMENT = "payment"
    FILE_UPLOAD = "file_upload"
    DOWNLOAD = "download"
    COOKIE_ACCESS = "cookie_access"
    LOCAL_STORAGE_ACCESS = "local_storage_access"
    PROFILE_ACCESS = "profile_access"
    EXTERNAL_SEND = "external_send"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BrowserAgentStatus:
    phase: str
    status: str
    execution_enabled: bool
    real_browser_control: str
    allowed_now: tuple[str, ...]
    blocked_now: tuple[str, ...]
    next_phase: str
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrowserActionSafetyDecision:
    action: str
    category: BrowserActionCategory
    decision: str
    allowed_now: bool
    reason: str
    required_future_gate: str
    safe_alternative: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrowserDomainPolicy:
    policy_name: str
    default_domain_mode: str
    public_page_preview_allowed: bool
    private_page_preview_allowed: bool
    logged_in_page_preview_allowed: bool
    cookies_allowed: bool
    local_storage_allowed: bool
    profile_access_allowed: bool
    passwords_allowed: bool
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrowserSessionPolicy:
    real_browser_control_enabled: bool
    launch_browser_allowed: bool
    navigate_allowed: bool
    click_allowed: bool
    type_allowed: bool
    submit_allowed: bool
    screenshot_allowed: bool
    screen_watch_allowed: bool
    automation_backends_enabled: tuple[str, ...]
    allowed_status_actions: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrowserBlockedAction:
    action: str
    category: BrowserActionCategory
    reason: str
    future_gate: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrowserCapabilityPreview:
    capability_id: str
    title: str
    allowed_now: bool
    execution_status: str
    safety_notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
