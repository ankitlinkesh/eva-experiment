from __future__ import annotations

from .backend_policy import backend_policy_text, get_backend_policy
from .observation_policy import boundary_lines, observation_policy_text
from .observer import observe_mock_page, observe_public_url
from .safety_filter import redaction_policy_text
from .session_policy import session_policy_text
from .status import get_browser_readonly_status
from .url_policy import blocked_url_classes_text, url_policy_text


def format_browser_read_status() -> str:
    status = get_browser_readonly_status()
    return "\n".join(
        [
            "Real Browser Read-Only Mode status",
            *boundary_lines(),
            f"Status: {status.status}.",
            f"Mode: {status.mode}.",
            f"Backend availability: {status.backend_mode}; available={status.backend_available}.",
            f"Deterministic mock fixture available: {status.mock_fixture_available}.",
            f"Public URLs only: {status.public_urls_only}.",
            f"Sessionless: {status.sessionless}; credentialless: {status.credentialless}.",
            f"Readiness: {status.readiness}.",
            f"Next phase: {status.next_phase}.",
        ]
    )


def format_browser_read_policy() -> str:
    return "\n\n".join(
        [
            observation_policy_text(),
            session_policy_text(),
            backend_policy_text(),
        ]
    )


def format_browser_read_url_policy() -> str:
    return url_policy_text()


def format_browser_read_observe(url: str | None = None) -> str:
    target = str(url or "").strip() or "https://example.com/"
    observation = observe_public_url(target)
    availability = "Backend availability: backend unavailable; no external request was made."
    return "\n".join([availability, observation.format()])


def format_browser_read_mock_observe() -> str:
    return observe_mock_page().format()


def format_browser_read_safety_report() -> str:
    return "\n\n".join(
        [
            "Real Browser Read-Only Mode safety report\n" + "\n".join(boundary_lines()),
            redaction_policy_text(),
            observe_mock_page().format(),
        ]
    )


def format_browser_read_blocked_urls() -> str:
    return blocked_url_classes_text()


def format_browser_read_readiness() -> str:
    status = get_browser_readonly_status()
    backend = get_backend_policy()
    return "\n".join(
        [
            "Real Browser Read-Only Mode readiness",
            *boundary_lines(),
            "Phase 24 core gate: complete.",
            "URL policy: ready and public-URL-only.",
            "Session isolation policy: ready; ephemeral, sessionless, credentialless, no-cookie, and no-profile.",
            "Phase 17 threat-defense integration: ready.",
            "Phase 20 execution-gate integration: ready for the read-only observation class only.",
            "Deterministic mock observation: ready.",
            f"Safe real backend: {backend.mode}; real public URLs fail closed with backend unavailable.",
            "Browser control remains locked and is not part of readiness.",
            f"Overall readiness: {status.readiness}.",
            f"Next phase: {status.next_phase}.",
        ]
    )
