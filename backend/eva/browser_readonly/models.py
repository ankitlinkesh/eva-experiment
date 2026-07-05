from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class URLSafetyDecision:
    requested_url: str
    normalized_url: str
    allowed: bool
    reason: str
    blocked_class: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SessionPolicy:
    mode: str
    ephemeral: bool
    sessionless: bool
    credentialless: bool
    cookies_allowed: bool
    profile_access_allowed: bool
    logged_in_browser_access_allowed: bool
    persistent_state_allowed: bool
    downloads_allowed: bool
    uploads_allowed: bool
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BackendPolicy:
    mode: str
    available: bool
    backend_name: str
    lazy_import_required: bool
    network_calls_in_tests: bool
    summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ObservationRequestDecision:
    request_summary: str
    allowed: bool
    decision: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BrowserObservation:
    observation_id: str
    requested_url: str
    normalized_url: str
    url_safety_decision: str
    backend_mode: str
    session_policy: str
    title_preview: str
    visible_text_summary: str
    link_summary: tuple[str, ...]
    blocked_content_notes: tuple[str, ...]
    redaction_status: str
    threat_scan_summary: str
    execution_gate_decision: str
    final_status: str
    no_click_statement: str
    no_type_statement: str
    no_form_submit_statement: str
    no_download_statement: str
    no_cookie_session_profile_statement: str
    no_tool_execution_statement: str
    no_new_write_path_statement: str
    safety_notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_browser_observation

        return format_browser_observation(self)


@dataclass(frozen=True)
class BrowserReadonlyStatus:
    status: str
    mode: str
    backend_mode: str
    backend_available: bool
    mock_fixture_available: bool
    public_urls_only: bool
    sessionless: bool
    credentialless: bool
    browser_control_enabled: bool
    tool_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    arbitrary_file_writes_enabled: bool
    readiness: str
    next_phase: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
