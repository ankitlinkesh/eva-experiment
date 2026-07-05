from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class BackendPolicy:
    mode: str
    available: bool
    backend_name: str
    lazy_import_required: bool
    real_screen_capture_in_tests: bool
    screenshot_saving_allowed: bool
    continuous_monitoring_allowed: bool
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
class CaptureGateDecision:
    request_summary: str
    allowed: bool
    decision: str
    reason: str
    one_shot_only: bool
    save_to_disk_allowed: bool
    continuous_monitoring_allowed: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SensitiveScreenClassification:
    category: str
    sensitive: bool
    confidence: str
    reason: str
    handling: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DesktopObservation:
    observation_id: str
    requested_observation_type: str
    backend_mode: str
    capture_gate_decision: str
    sensitive_screen_classification: str
    redaction_status: str
    visible_summary_preview: str
    app_window_metadata_preview: tuple[str, ...]
    blocked_content_notes: tuple[str, ...]
    threat_scan_summary: str
    execution_gate_decision: str
    final_status: str
    no_click_statement: str
    no_type_statement: str
    no_hotkey_statement: str
    no_app_control_statement: str
    no_continuous_monitoring_statement: str
    no_screenshot_save_statement: str
    no_cookie_session_profile_statement: str
    no_tool_execution_statement: str
    no_new_write_path_statement: str
    safety_notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    def format(self) -> str:
        from .report import format_desktop_observation

        return format_desktop_observation(self)


@dataclass(frozen=True)
class DesktopObservationStatus:
    status: str
    mode: str
    backend_mode: str
    backend_available: bool
    mock_fixture_available: bool
    explicit_user_trigger_required: bool
    desktop_control_enabled: bool
    continuous_monitoring_enabled: bool
    screenshot_saving_enabled: bool
    tool_execution_enabled: bool
    arbitrary_file_reads_enabled: bool
    arbitrary_file_writes_enabled: bool
    readiness: str
    next_phase: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)
