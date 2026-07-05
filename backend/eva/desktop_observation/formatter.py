from __future__ import annotations

from .backend_policy import backend_policy_text, get_backend_policy
from .capture_gate import capture_gate_policy_text
from .observation_policy import boundary_lines, observation_policy_text
from .observer import observe_mock_desktop
from .redaction import redaction_policy_text
from .sensitive_screen import sensitive_screen_policy_text
from .status import get_desktop_observation_status


def format_desktop_observe_status() -> str:
    status = get_desktop_observation_status()
    return "\n".join(
        [
            "Real Desktop Observation Mode status",
            *boundary_lines(),
            f"Status: {status.status}.",
            f"Mode: {status.mode}.",
            f"Backend availability: {status.backend_mode}; available={status.backend_available}.",
            f"Deterministic mock fixture available: {status.mock_fixture_available}.",
            f"Explicit user trigger required: {status.explicit_user_trigger_required}.",
            f"Readiness: {status.readiness}.",
            f"Next phase: {status.next_phase}.",
        ]
    )


def format_desktop_observe_policy() -> str:
    return "\n\n".join(
        (
            observation_policy_text(),
            capture_gate_policy_text(),
            backend_policy_text(),
        )
    )


def format_desktop_observe_backend() -> str:
    return backend_policy_text()


def format_desktop_observe_mock() -> str:
    return observe_mock_desktop().format()


def format_desktop_observe_safety_report() -> str:
    return "\n\n".join(
        (
            "Real Desktop Observation Mode safety report\n" + "\n".join(boundary_lines()),
            sensitive_screen_policy_text(),
            redaction_policy_text(),
            observe_mock_desktop().format(),
        )
    )


def format_desktop_observe_sensitive_screens() -> str:
    return sensitive_screen_policy_text()


def format_desktop_observe_redaction_policy() -> str:
    return redaction_policy_text()


def format_desktop_observe_readiness() -> str:
    status = get_desktop_observation_status()
    backend = get_backend_policy()
    return "\n".join(
        [
            "Real Desktop Observation Mode readiness",
            *boundary_lines(),
            "Phase 25 core gate: complete.",
            "Observation policy: explicit, user-triggered, one-shot, and control-free.",
            "Capture gate: ready; no persistence or background activity.",
            "Sensitive-screen classification and redaction: ready.",
            "Phase 17 threat-defense integration: ready.",
            "Phase 20 execution-gate integration: ready for observation-only reports.",
            "Deterministic mock observation: ready.",
            f"Safe real backend: {backend.mode}; real observations fail closed with backend unavailable.",
            "Desktop control remains locked and is not part of readiness.",
            f"Overall readiness: {status.readiness}.",
            f"Next phase: {status.next_phase}.",
        ]
    )
