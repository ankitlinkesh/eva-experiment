from __future__ import annotations

from .models import DesktopObservationReadiness


def get_desktop_observation_readiness() -> DesktopObservationReadiness:
    return DesktopObservationReadiness(
        status="preview only",
        ready_for_preview_records=True,
        ready_for_real_observation=False,
        ready_for_real_control=False,
        allowed_now=(
            "desktop session status previews",
            "preview-only desktop session records",
            "app/window/active-context schema previews",
            "readiness gap explanations",
            "locked boundary explanations",
        ),
        gaps=(
            "no real screen capture, screenshots, or active screen reads are enabled",
            "no real window enumeration or active app detection is enabled",
            "no app launch, mouse, keyboard, clipboard, or file-dialog automation is enabled",
            "no terminal, shell, package, browser, desktop, PyAutoGUI, Playwright, MCP, or cloud execution is enabled",
            "no permission-gated observation session exists for private windows yet",
            "no high-confidence UI target verifier exists for future desktop actions yet",
            "no rollback/audit executor exists for real desktop actions yet",
        ),
        next_phase="Phase 14G locked readiness proof is complete. Future observation/control needs a separate approved gate; the current architecture track is Phase 15 LLM Router + Structured Reasoning Core.",
        summary="Desktop sessions are preview/status records only. Real desktop observation and control remain locked.",
    )
