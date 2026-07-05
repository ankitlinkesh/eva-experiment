from __future__ import annotations

from .models import DesktopCapabilityCategory, DesktopCapabilityPreview


def list_desktop_capability_previews() -> tuple[DesktopCapabilityPreview, ...]:
    return (
        DesktopCapabilityPreview("desktop.status", "DesktopAgent Status", DesktopCapabilityCategory.STATUS_ONLY, True, "read_only_metadata", "Status only; no desktop observation/control."),
        DesktopCapabilityPreview("desktop.policy", "DesktopAgent Policy", DesktopCapabilityCategory.STATUS_ONLY, True, "read_only_metadata", "Policy only; no screen or app state read."),
        DesktopCapabilityPreview("desktop.blocked_actions", "Desktop Blocked Actions", DesktopCapabilityCategory.STATUS_ONLY, True, "read_only_metadata", "Explains blocked actions only."),
        DesktopCapabilityPreview("desktop.action_safety_preview", "Desktop Action Safety Preview", DesktopCapabilityCategory.AUTOMATION_PREVIEW, True, "read_only_metadata", "Classifies requested action text only."),
        DesktopCapabilityPreview("desktop.app_risk", "Desktop App Risk", DesktopCapabilityCategory.APP_STATUS_PREVIEW, True, "read_only_metadata", "Classifies app/category string only."),
        DesktopCapabilityPreview("desktop.readiness", "Desktop Readiness", DesktopCapabilityCategory.STATUS_ONLY, True, "read_only_metadata", "Shows gaps before future DesktopAgent execution."),
        DesktopCapabilityPreview("desktop.session_status", "Desktop Session Status", DesktopCapabilityCategory.STATUS_ONLY, True, "read_only_metadata", "Preview session status only; no desktop observation/control."),
        DesktopCapabilityPreview("desktop.sessions_list", "Desktop Sessions List", DesktopCapabilityCategory.STATUS_ONLY, True, "read_only_metadata", "Lists in-memory preview records only."),
        DesktopCapabilityPreview("desktop.session_preview", "Desktop Session Preview", DesktopCapabilityCategory.STATUS_ONLY, True, "read_only_metadata", "Creates preview-only record; no screen/window/app inspection."),
        DesktopCapabilityPreview("desktop.session_plan", "Desktop Session Plan", DesktopCapabilityCategory.STATUS_ONLY, True, "read_only_metadata", "Shows future session lifecycle only."),
        DesktopCapabilityPreview("desktop.app_status_preview", "Desktop App Status Preview", DesktopCapabilityCategory.APP_STATUS_PREVIEW, True, "read_only_metadata", "Shows future app status schema only."),
        DesktopCapabilityPreview("desktop.window_status_preview", "Desktop Window Status Preview", DesktopCapabilityCategory.WINDOW_STATUS_PREVIEW, True, "read_only_metadata", "Shows future window status schema only."),
        DesktopCapabilityPreview("desktop.active_context_preview", "Desktop Active Context Preview", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Shows future active context schema only."),
        DesktopCapabilityPreview("desktop.observation_readiness", "Desktop Observation Readiness", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Shows observation readiness gaps only."),
        DesktopCapabilityPreview("desktop.screen_policy", "Desktop Screen Policy", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Shows locked screen observation policy only."),
        DesktopCapabilityPreview("desktop.screen_observation_policy", "Desktop Screen Observation Policy", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Shows future screen observation schema only."),
        DesktopCapabilityPreview("desktop.sensitive_screens", "Desktop Sensitive Screens", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Lists sensitive screen categories only."),
        DesktopCapabilityPreview("desktop.screen_redaction_policy", "Desktop Screen Redaction Policy", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Shows future redaction policy only."),
        DesktopCapabilityPreview("desktop.screen_capture_gate", "Desktop Screen Capture Gate", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Shows locked capture gate requirements only."),
        DesktopCapabilityPreview("desktop.screen_readiness", "Desktop Screen Readiness", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Shows gaps before future screen observation."),
        DesktopCapabilityPreview("desktop.observation_policy", "Desktop Observation Policy", DesktopCapabilityCategory.SCREEN_OBSERVATION_PREVIEW, True, "read_only_metadata", "Shows policy and safety decision preview only."),
    )
