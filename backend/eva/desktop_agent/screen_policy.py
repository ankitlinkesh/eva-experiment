from __future__ import annotations

from .models import (
    DesktopScreenObservationPolicy,
    DesktopScreenObservationReadiness,
    DesktopScreenObservationSafetyDecision,
    DesktopSensitiveScreenCategory,
)


ALLOWED_SCREEN_POLICY_ACTIONS: tuple[str, ...] = (
    "screen observation policy summary",
    "sensitive screen category explanations",
    "redaction policy preview",
    "future capture gate requirements",
    "observation readiness gaps",
    "Control Center screen observation locked panel",
)

BLOCKED_SCREEN_OBSERVATION_ACTIONS: tuple[str, ...] = (
    "real screen capture",
    "screenshots",
    "OCR",
    "image or screen analysis",
    "real window/app inspection",
    "active app/window detection",
    "mouse movement, clicking, or dragging",
    "keyboard typing or hotkeys",
    "clipboard read/write",
    "file dialog automation",
    "terminal, shell, or package execution",
    "browser/desktop automation",
    "PyAutoGUI, Playwright, MCP, cloud, or package calls",
    "secret, token, cookie, password, browser-session, and private-data reads",
)


def list_sensitive_screen_categories() -> tuple[DesktopSensitiveScreenCategory, ...]:
    return tuple(DesktopSensitiveScreenCategory)


def get_desktop_screen_policy() -> DesktopScreenObservationPolicy:
    return DesktopScreenObservationPolicy(
        mode="policy_preview_only",
        real_screen_capture_allowed=False,
        screenshots_allowed=False,
        ocr_allowed=False,
        image_analysis_allowed=False,
        cloud_screen_sharing_allowed=False,
        allowed_now=ALLOWED_SCREEN_POLICY_ACTIONS,
        blocked_now=BLOCKED_SCREEN_OBSERVATION_ACTIONS,
        sensitive_categories=tuple(item.value for item in list_sensitive_screen_categories()),
        future_requirements=(
            "explicit user-commanded observation gate",
            "private/sensitive screen classifier before capture",
            "local redaction policy before any summary",
            "separate confirmation before any future capture",
            "override requirement for sensitive screens",
            "local-only storage and audit evidence",
            "separate confirmation before any future cloud sharing",
        ),
    )


def get_desktop_screen_observation_readiness() -> DesktopScreenObservationReadiness:
    policy = get_desktop_screen_policy()
    return DesktopScreenObservationReadiness(
        status="policy preview only",
        ready_for_policy_preview=True,
        ready_for_real_capture=False,
        ready_for_redacted_observation=False,
        allowed_now=policy.allowed_now,
        gaps=(
            "no real capture or screenshot adapter is enabled",
            "no OCR or image analysis is enabled",
            "no sensitive-screen classifier is active",
            "no permission session exists for screen capture",
            "no local redaction/verification loop exists for real frames",
            "no audit checkpoint exists for future screen observation",
        ),
        next_phase="Keyboard/Mouse Action Dry-Run Schema",
        summary="Desktop screen observation is policy/status only. Real capture, screenshots, OCR, and image analysis remain locked.",
    )


def evaluate_screen_observation_safety(request: str) -> DesktopScreenObservationSafetyDecision:
    text = " ".join(str(request or "").lower().split())
    if any(term in text for term in ("screenshot", "screen capture", "capture screen", "see my screen", "read my screen", "inspect my screen", "ocr")):
        category = "screen_observation"
        reason = "Real screen observation is locked in Phase 14C. Eva can explain the policy, redaction plan, and future capture gate only."
    else:
        category = "unknown_screen_observation"
        reason = "Unknown screen observation requests stay locked until a future explicit observation gate exists."
    return DesktopScreenObservationSafetyDecision(
        request=str(request or "").strip() or "unknown",
        category=category,
        decision="locked",
        allowed_now=False,
        reason=reason,
        required_future_gate="Future user-approved screen observation gate with sensitive-screen policy, redaction, local audit, verification, and no cloud sharing unless separately confirmed.",
        safe_alternative="Use `eva desktop screen policy`, `eva desktop screen redaction policy`, or `eva desktop screen readiness` for the current locked status.",
    )
