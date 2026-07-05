from __future__ import annotations

from .models import SessionPolicy
from .observation_policy import boundary_lines


def get_session_policy() -> SessionPolicy:
    return SessionPolicy(
        mode="isolated ephemeral read-only observation",
        ephemeral=True,
        sessionless=True,
        credentialless=True,
        cookies_allowed=False,
        profile_access_allowed=False,
        logged_in_browser_access_allowed=False,
        persistent_state_allowed=False,
        downloads_allowed=False,
        uploads_allowed=False,
        summary="Each observation is isolated, has no reusable identity, and retains no browser state.",
    )


def session_policy_text() -> str:
    policy = get_session_policy()
    return "\n".join(
        [
            "Real Browser Read-Only Mode session policy",
            *boundary_lines(),
            f"Mode: {policy.mode}.",
            "Every observation is isolated and ephemeral.",
            "No cookies, local storage, saved credentials, password manager, or browser-profile state is available.",
            "The user's existing Chrome, Edge, or other logged-in session is never attached or read.",
            "No state is persisted between observations.",
        ]
    )
