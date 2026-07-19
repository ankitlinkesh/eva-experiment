"""Verify an AgentAction's declared post-condition (Phase 38 lineage).

Phase 69: before this, every method here except ``file_exists``/
``file_contains`` set ``verified = bool(observation.success)`` -- i.e. it
trusted the *actor's own self-report* and dressed that up as a 0.65/0.75/0.8-
confidence "verification". That is precisely the self-report-laundering
defect Phase 64 fixed in ``tools/postconditions.py`` (see that module's
docstring), left uncorrected in this second, older copy: this module predates
``tools/postconditions.py`` and was never migrated when the honesty fix
landed there.

Rather than re-encode the same honesty rules a second time here -- duplicating
them is exactly why the bug survived Phase 64 in the first place, since the
fix only touched one of the two copies -- ``verify_action`` now delegates to
``tools.postconditions.verify_tool_effect`` (the same machinery
``agent/executor.py`` already uses for the main ToolRegistry execution path)
and translates the result into this module's ``VerificationResult`` shape.

``tools/postconditions.py`` is deliberately pure (no registry import, to avoid
an import cycle); importing it here is safe for the same reason -- this
module only calls into it, it does not import anything that imports back.
"""

from __future__ import annotations

from typing import Any

from .action_model import AgentAction, AgentObservation, VerificationResult
from ..tools.postconditions import PROVENANCE_UNVERIFIED, verify_tool_effect


def verify_action(action: AgentAction, observation: AgentObservation) -> VerificationResult:
    try:
        method = str(action.verification.get("method") or "command_result_success")

        # action.verification takes precedence over action.params for
        # path/text -- preserved from the pre-Phase-69 file_exists/
        # file_contains branches below (the two paths that were already
        # honest). Folded into one args dict for derive_postcondition, which
        # tries several synonym keys per method (query/app/target,
        # dst/dest/target/path, content/text, ...).
        args: dict[str, Any] = dict(action.params or {})
        verification_path = action.verification.get("path")
        if verification_path:
            args["path"] = verification_path
        verification_text = action.verification.get("text")
        if verification_text:
            # derive_postcondition's file_contains branch tries "content"
            # before "text"; drop any params-derived "content" so the
            # verification-supplied text (which must win) is what gets used.
            args.pop("content", None)
            args["text"] = verification_text

        # observation.success is the actor's OWN self-report -- the thing
        # this whole phase exists to stop trusting blindly. Shape it as the
        # dict tools.postconditions._result_reports_success actually reads,
        # with observation.success as the authoritative "ok": a False
        # self-report must map to a falsy result, never silently read as
        # success (passing observation.success straight through would only
        # matter for the command_result_success branch, but get this wrong
        # and a failed observation reads as success there).
        result_payload: dict[str, Any] = dict(observation.raw_observation or {})
        result_payload["ok"] = bool(observation.success)
        if observation.error:
            result_payload["error"] = observation.error

        outcome = verify_tool_effect(action.tool_name, method, args, result_payload)

        return VerificationResult(
            action_id=action.action_id,
            verified=outcome.verified,
            confidence=outcome.confidence,
            evidence=outcome.detail,
            failure_reason=None if outcome.verified else (observation.error or outcome.method),
            suggested_repair=outcome.remediation,
            independent=outcome.independent,
            provenance=outcome.provenance,
        )
    except Exception as exc:  # fail-safe: never raise into the caller
        return VerificationResult(
            action_id=action.action_id,
            verified=False,
            confidence=0.2,
            evidence=f"verification error: {type(exc).__name__}: {exc}",
            failure_reason="verification_error",
            suggested_repair="verify manually",
            independent=False,
            provenance=PROVENANCE_UNVERIFIED,
        )
