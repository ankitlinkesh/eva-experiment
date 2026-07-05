from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class DesktopCapabilityCategory(StrEnum):
    STATUS_ONLY = "status_only"
    APP_STATUS_PREVIEW = "app_status_preview"
    WINDOW_STATUS_PREVIEW = "window_status_preview"
    SCREEN_OBSERVATION_PREVIEW = "screen_observation_preview"
    MOUSE_ACTION_PREVIEW = "mouse_action_preview"
    KEYBOARD_ACTION_PREVIEW = "keyboard_action_preview"
    CLIPBOARD_PREVIEW = "clipboard_preview"
    FILE_DIALOG_PREVIEW = "file_dialog_preview"
    APP_LAUNCH_PREVIEW = "app_launch_preview"
    AUTOMATION_PREVIEW = "automation_preview"
    UNKNOWN = "unknown"


class DesktopActionCategory(StrEnum):
    DESKTOP_STATUS = "desktop_status"
    APP_STATUS = "app_status"
    WINDOW_STATUS = "window_status"
    SCREEN_CAPTURE = "screen_capture"
    SCREENSHOT = "screenshot"
    APP_LAUNCH = "app_launch"
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_DRAG = "mouse_drag"
    KEYBOARD_TYPE = "keyboard_type"
    HOTKEY = "hotkey"
    CLIPBOARD_READ = "clipboard_read"
    CLIPBOARD_WRITE = "clipboard_write"
    FILE_DIALOG = "file_dialog"
    TERMINAL_SHELL = "terminal_shell"
    INSTALL_PACKAGE = "install_package"
    EXTERNAL_SEND = "external_send"
    UNKNOWN = "unknown"


class DesktopAppRiskLevel(StrEnum):
    SAFE_STATUS_ONLY = "safe_status_only"
    NORMAL_APP = "normal_app"
    SENSITIVE_PERSONAL = "sensitive_personal"
    CREDENTIALS_OR_SECRETS = "credentials_or_secrets"
    FINANCIAL_OR_PAYMENT = "financial_or_payment"
    MESSAGING_OR_EXTERNAL_SEND = "messaging_or_external_send"
    FILE_SYSTEM_SENSITIVE = "file_system_sensitive"
    SYSTEM_SETTINGS = "system_settings"
    TERMINAL_OR_CODE_EXECUTION = "terminal_or_code_execution"
    UNKNOWN_HIGH_RISK = "unknown_high_risk"
    BLOCKED = "blocked"


class DesktopAppCategory(StrEnum):
    STATUS_SURFACE = "status_surface"
    PRODUCTIVITY = "productivity"
    PERSONAL_DATA = "personal_data"
    SECRET_STORE = "secret_store"
    FINANCE = "finance"
    MESSAGING = "messaging"
    FILE_MANAGER = "file_manager"
    SYSTEM_SETTINGS = "system_settings"
    TERMINAL = "terminal"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DesktopAgentStatus:
    phase: str
    status: str
    execution_enabled: bool
    real_screen_observation: str
    real_desktop_control: str
    allowed_now: tuple[str, ...]
    blocked_now: tuple[str, ...]
    next_phase: str
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopActionSafetyDecision:
    action: str
    category: DesktopActionCategory
    decision: str
    allowed_now: bool
    reason: str
    required_future_gate: str
    safe_alternative: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopAppRisk:
    query: str
    category: DesktopAppCategory
    risk_level: DesktopAppRiskLevel
    allowed_for_control_now: bool
    reason: str
    safe_alternative: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopCapabilityPreview:
    capability_id: str
    title: str
    category: DesktopCapabilityCategory
    allowed_now: bool
    execution_status: str
    safety_notes: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopBlockedAction:
    action: str
    category: DesktopActionCategory
    reason: str
    future_gate: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class DesktopSessionMode(StrEnum):
    LOCKED = "locked"
    PREVIEW_ONLY = "preview_only"
    FUTURE_OBSERVATION = "future_observation"
    FUTURE_CONTROLLED = "future_controlled"


class DesktopSessionStatus(StrEnum):
    NOT_STARTED = "not_started"
    PREVIEW_PLANNED = "preview_planned"
    LOCKED = "locked"
    BLOCKED = "blocked"
    CLOSED = "closed"


class DesktopScreenObservationMode(StrEnum):
    LOCKED = "locked"
    POLICY_PREVIEW_ONLY = "policy_preview_only"
    FUTURE_REDACTED_OBSERVATION = "future_redacted_observation"
    FUTURE_USER_APPROVED_CAPTURE = "future_user_approved_capture"
    BLOCKED = "blocked"


class DesktopSensitiveScreenCategory(StrEnum):
    PASSWORDS_OR_CREDENTIALS = "passwords_or_credentials"
    BANKING_OR_PAYMENT = "banking_or_payment"
    PERSONAL_MESSAGES = "personal_messages"
    EMAIL_INBOX = "email_inbox"
    PRIVATE_DOCUMENTS = "private_documents"
    BROWSER_SESSIONS = "browser_sessions"
    TOKENS_OR_SECRETS = "tokens_or_secrets"
    CODE_WITH_SECRETS = "code_with_secrets"
    SYSTEM_SETTINGS = "system_settings"
    FILE_MANAGER_SENSITIVE = "file_manager_sensitive"
    UNKNOWN_SENSITIVE = "unknown_sensitive"


@dataclass(frozen=True)
class DesktopSessionPreview:
    session_id: str
    label: str
    mode: str
    status: str
    app_window_policy_summary: str
    allowed_now: tuple[str, ...]
    blocked_now: tuple[str, ...]
    created_at: str
    updated_at: str
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopAppStatusPreview:
    title: str
    mode: str
    real_app_inspection: bool
    schema_fields: tuple[str, ...]
    blocked_fields: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopWindowStatusPreview:
    title: str
    mode: str
    real_window_enumeration: bool
    schema_fields: tuple[str, ...]
    blocked_fields: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopActiveContextPreview:
    title: str
    mode: str
    real_active_app_detection: bool
    schema_fields: tuple[str, ...]
    blocked_fields: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopObservationReadiness:
    status: str
    ready_for_preview_records: bool
    ready_for_real_observation: bool
    ready_for_real_control: bool
    allowed_now: tuple[str, ...]
    gaps: tuple[str, ...]
    next_phase: str
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopSessionRegistryResult:
    status: str
    sessions_count: int
    latest_session_id: str | None
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopScreenObservationPolicy:
    mode: str
    real_screen_capture_allowed: bool
    screenshots_allowed: bool
    ocr_allowed: bool
    image_analysis_allowed: bool
    cloud_screen_sharing_allowed: bool
    allowed_now: tuple[str, ...]
    blocked_now: tuple[str, ...]
    sensitive_categories: tuple[str, ...]
    future_requirements: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopScreenObservationPreview:
    title: str
    mode: str
    real_capture_performed: bool
    schema_fields: tuple[str, ...]
    blocked_fields: tuple[str, ...]
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopScreenObservationSafetyDecision:
    request: str
    category: str
    decision: str
    allowed_now: bool
    reason: str
    required_future_gate: str
    safe_alternative: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopScreenRedactionRule:
    name: str
    category: str
    replacement: str
    note: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopScreenObservationReadiness:
    status: str
    ready_for_policy_preview: bool
    ready_for_real_capture: bool
    ready_for_redacted_observation: bool
    allowed_now: tuple[str, ...]
    gaps: tuple[str, ...]
    next_phase: str
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopScreenCaptureGate:
    status: str
    capture_allowed_now: bool
    exact_user_command_required: bool
    confirmation_required: bool
    override_required_for_sensitive_screens: bool
    blocked_now: tuple[str, ...]
    future_requirements: tuple[str, ...]
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
