from __future__ import annotations

from .models import BackendPolicy
from .observation_policy import boundary_lines


def get_backend_policy() -> BackendPolicy:
    return BackendPolicy(
        mode="unavailable",
        available=False,
        backend_name="none",
        lazy_import_required=True,
        network_calls_in_tests=False,
        summary="No pre-existing safe read-only browser backend is configured; real URL observations fail closed.",
    )


def backend_policy_text() -> str:
    policy = get_backend_policy()
    return "\n".join(
        [
            "Real Browser Read-Only Mode backend policy",
            *boundary_lines(),
            f"Backend mode: {policy.mode}.",
            f"Backend available: {policy.available}.",
            "No Playwright, Selenium, browser driver, provider SDK, or new dependency is installed or imported.",
            "Deterministic mock fixtures are available for local verification.",
            "A public URL may pass URL policy while still returning backend unavailable.",
            "Any future safe backend must be separately reviewed, lazy-loaded, redirect-safe, DNS-rebinding-safe, no-cookie, no-profile, no-download, and ephemeral.",
        ]
    )
