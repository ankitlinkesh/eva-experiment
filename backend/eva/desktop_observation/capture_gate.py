from __future__ import annotations

from .models import CaptureGateDecision
from .observation_policy import boundary_lines, evaluate_observation_request


_EXPLICIT_MARKERS = ("explicit", "one-shot", "one shot", "observe", "observation", "read only", "mock")


def evaluate_capture_gate(request: str) -> CaptureGateDecision:
    policy = evaluate_observation_request(request)
    lowered = policy.request_summary.lower()
    if not policy.allowed:
        return CaptureGateDecision(
            request_summary=policy.request_summary,
            allowed=False,
            decision="blocked_by_observation_policy",
            reason=policy.reason,
            one_shot_only=True,
            save_to_disk_allowed=False,
            continuous_monitoring_allowed=False,
        )
    if not any(marker in lowered for marker in _EXPLICIT_MARKERS):
        return CaptureGateDecision(
            request_summary=policy.request_summary,
            allowed=False,
            decision="explicit_user_trigger_required",
            reason="Desktop observation requires an explicit one-shot user request.",
            one_shot_only=True,
            save_to_disk_allowed=False,
            continuous_monitoring_allowed=False,
        )
    return CaptureGateDecision(
        request_summary=policy.request_summary,
        allowed=True,
        decision="allowed_observation_only",
        reason="Explicit one-shot observation/report output is allowed; capture persistence and control are unavailable.",
        one_shot_only=True,
        save_to_disk_allowed=False,
        continuous_monitoring_allowed=False,
    )


def capture_gate_policy_text() -> str:
    return "\n".join(
        [
            "Real Desktop Observation Mode capture gate policy",
            *boundary_lines(),
            "An explicit user-triggered one-shot request is required.",
            "The gate returns policy metadata only when no safe backend is configured.",
            "Mock fixtures never touch the real screen.",
            "The gate cannot authorize mouse, keyboard, clipboard, app/window, persistence, or background activity.",
            "Capture data cannot be written to disk.",
        ]
    )
