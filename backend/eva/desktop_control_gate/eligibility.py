from __future__ import annotations

from .action_catalog import classify_action
from .models import EligibilityDecision


def evaluate_action_eligibility(request: str, *, sensitive_screen: bool = False) -> EligibilityDecision:
    action_class = classify_action(request)
    if sensitive_screen:
        state, reason = "denied_sensitive_screen", "Sensitive-screen context blocks future control."
    elif action_class == "credential_or_secret_candidate":
        state, reason = "denied_secret_or_credential_risk", "Secret, credential, session, and cookie actions are always blocked."
    elif action_class == "destructive_or_irreversible_candidate":
        state, reason = "denied_destructive_action", "Destructive or irreversible desktop actions are blocked."
    elif action_class == "unknown_or_hallucinated_action":
        state, reason = "denied_unknown_capability", "Unknown or hallucinated desktop capabilities are denied."
    elif action_class in {"shell_or_terminal_candidate", "package_install_candidate", "file_write_candidate", "browser_control_candidate"}:
        state, reason = "blocked_by_policy", "This action class is outside the desktop-control gate."
    elif action_class == "observe_only_reference":
        state, reason = "preview_only", "Phase 25 observation may be referenced as status only."
    else:
        state, reason = "requires_future_desktop_control_gate", "Future control candidate; execution remains unavailable."
    return EligibilityDecision(
        action_class=action_class,
        gate_decision=state,
        permission_class="observation_only" if action_class == "observe_only_reference" else "future_control_candidate",
        execution_allowed=False,
        approval_required=action_class not in {"observe_only_reference", "credential_or_secret_candidate", "destructive_or_irreversible_candidate", "unknown_or_hallucinated_action"},
        exact_confirmation_required=action_class not in {"observe_only_reference", "credential_or_secret_candidate", "destructive_or_irreversible_candidate", "unknown_or_hallucinated_action"},
        reason=reason,
    )


def eligibility_policy_text() -> str:
    return "\n".join((
        "Desktop control eligibility policy",
        "Every result is preview-only and execution_allowed is always false.",
        "Approval or confirmation metadata cannot unlock an action.",
    ))
