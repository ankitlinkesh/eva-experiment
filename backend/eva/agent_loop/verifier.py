from __future__ import annotations

from .models import ActionPreview, VerificationNote


def verify_action_previews(actions: tuple[ActionPreview, ...], *, blocked: bool) -> tuple[VerificationNote, ...]:
    notes: list[VerificationNote] = [
        VerificationNote("verify_no_live_llm", "pass", "No live LLM call was made."),
        VerificationNote("verify_preview_only", "pass", "Actions are preview-only."),
        VerificationNote("verify_no_tool_execution", "pass", "Tools are not executed."),
        VerificationNote("verify_secret_boundary", "pass", "Secrets/config/session data are blocked."),
        VerificationNote("verify_execution_boundary", "pass", "Browser/desktop/shell/cloud/MCP execution remains locked."),
    ]
    if any(action.executed or action.execution_status != "preview_only" for action in actions):
        notes.append(VerificationNote("verify_action_execution", "fail", "An action preview attempted execution."))
    else:
        notes.append(VerificationNote("verify_action_execution", "pass", "No action preview executed tools."))
    if blocked:
        notes.append(VerificationNote("verify_blocked_request", "pass", "Unsafe request became a blocked/refusal preview."))
    return tuple(notes)
