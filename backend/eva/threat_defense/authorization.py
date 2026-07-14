"""The authorization moat: untrusted content proposes, it never authorizes (P40).

The permission gate already decides *what class* a tool is (allow / confirm /
override). This module adds the orthogonal question the gate can't see: *who
motivated this call?* If a privileged action was proposed while the agent's
context is carrying injected, untrusted content, that action must not run on the
untrusted content's say-so — it escalates to an explicit human confirmation that
names the risk. A web page that says "delete all my files" can be *read*, and
Eva may even plan a delete because of it, but the delete can never fire without
the user knowingly approving it.

This is a policy layer the agent loop consults; the permission gate remains the
final authority for execution. Pure and fail-safe: on any error it escalates
(fails safe) rather than allowing.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorizationDecision:
    """Whether a proposed action may proceed given who motivated it."""

    allow: bool
    escalate: bool
    injection_suspected: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "allow": self.allow,
            "escalate": self.escalate,
            "injection_suspected": self.injection_suspected,
            "reason": self.reason,
        }


def authorize_action(*, tool_privileged: bool, context_tainted: bool, injection_detected: bool) -> AuthorizationDecision:
    """Decide whether a proposed tool call may run on its current provenance.

    - Unprivileged (allow-class) tools are always permitted here — a bounded
      local read cannot be turned into harm, so untrusted motivation is fine.
    - A privileged tool proposed while injected/untrusted content is in context
      can NEVER be auto-authorized. It escalates to explicit user confirmation
      carrying an injection warning. Untrusted content proposed it; only the
      user can authorize it.
    - A privileged tool with clean context is left to the normal gate flow
      (this layer allows; the gate still governs confirmation as usual).
    """
    try:
        if not tool_privileged:
            return AuthorizationDecision(
                allow=True,
                escalate=False,
                injection_suspected=False,
                reason="Unprivileged action; untrusted content may motivate a bounded read.",
            )

        if context_tainted and injection_detected:
            return AuthorizationDecision(
                allow=False,
                escalate=True,
                injection_suspected=True,
                reason=(
                    "A privileged action was proposed while injected, untrusted content is in "
                    "context. Untrusted content can propose but never authorize — requiring "
                    "explicit user confirmation."
                ),
            )

        return AuthorizationDecision(
            allow=True,
            escalate=False,
            injection_suspected=False,
            reason="Privileged action with untainted context; the permission gate governs it.",
        )
    except Exception:
        # Fail safe: never allow on error.
        return AuthorizationDecision(
            allow=False,
            escalate=True,
            injection_suspected=True,
            reason="Authorization check failed; escalating to confirmation as a safe default.",
        )
