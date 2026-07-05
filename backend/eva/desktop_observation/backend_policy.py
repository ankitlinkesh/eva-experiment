from __future__ import annotations

from .models import BackendPolicy
from .observation_policy import boundary_lines


def get_backend_policy() -> BackendPolicy:
    return BackendPolicy(
        mode="unavailable",
        available=False,
        backend_name="none",
        lazy_import_required=True,
        real_screen_capture_in_tests=False,
        screenshot_saving_allowed=False,
        continuous_monitoring_allowed=False,
        summary="No pre-existing safe one-shot desktop observation backend is configured; real observations fail closed.",
    )


def backend_policy_text() -> str:
    policy = get_backend_policy()
    return "\n".join(
        [
            "Real Desktop Observation Mode backend policy",
            *boundary_lines(),
            f"Backend mode: {policy.mode}.",
            f"Backend available: {policy.available}.",
            "No screenshot, OCR, desktop automation, provider SDK, or new dependency is installed or imported.",
            "Deterministic mock screen fixtures are available for local verification.",
            "A real observation request returns backend unavailable without touching the real screen.",
            "Any future safe backend must be separately reviewed, lazy-loaded, one-shot, memory-only, redaction-first, and control-free.",
        ]
    )
