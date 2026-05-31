from __future__ import annotations

from pathlib import Path

from .action_model import AgentAction, AgentObservation, VerificationResult


def verify_action(action: AgentAction, observation: AgentObservation) -> VerificationResult:
    method = str(action.verification.get("method") or "command_result_success")
    if method == "file_exists":
        path = Path(str(action.verification.get("path") or action.params.get("path") or ""))
        ok = path.exists()
        return VerificationResult(action.action_id, ok, 0.95 if ok else 0.1, f"file_exists={ok}", None if ok else "file_missing")
    if method == "file_contains":
        path = Path(str(action.verification.get("path") or action.params.get("path") or ""))
        text = str(action.verification.get("text") or action.params.get("content") or "")
        ok = path.exists() and text in path.read_text(encoding="utf-8", errors="replace")
        return VerificationResult(action.action_id, ok, 0.95 if ok else 0.25, f"file_contains={ok}", None if ok else "expected_text_missing", "restore checkpoint or rewrite file")
    if method in {"app_window_active", "url_opened", "screen_state_changed"}:
        ok = bool(observation.success)
        return VerificationResult(action.action_id, ok, 0.75 if ok else 0.35, observation.summary, None if ok else "local_observation_uncertain")
    if method in {"message_draft_prepared", "message_sent_likely", "text_field_contains"}:
        ok = bool(observation.success)
        return VerificationResult(action.action_id, ok, 0.65 if ok else 0.3, observation.summary, None if ok else "message_state_uncertain", "ask user to confirm visible state")
    if method == "no_verification_available":
        return VerificationResult(action.action_id, False, 0.2, "No verification method available.", "unverified", "ask user to verify")
    ok = bool(observation.success)
    return VerificationResult(action.action_id, ok, 0.8 if ok else 0.3, observation.summary, None if ok else observation.error)
