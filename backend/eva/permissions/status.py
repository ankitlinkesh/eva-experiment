from __future__ import annotations

from .ledger import cancel_pending_action, confirm_pending_action, get_pending_action, list_pending_actions, pending_action_ledger_status
from .pending_actions import EvaPendingAction, EvaPendingActionResult


def format_pending_actions() -> str:
    actions = list_pending_actions()
    if not actions:
        return "No pending actions."
    lines = ["Pending actions", ""]
    for index, action in enumerate(actions, start=1):
        lines.extend(
            [
                f"{index}. {action.id}",
                f"Status: {action.status}",
                f"Risk: {action.risk_category}",
                f"Summary: {action.summary}",
                f"Expires: {action.expires_at}",
                "",
                "Say:",
                f"`{'confirm override' if action.requires_override else 'confirm'} {action.id}`",
                "or",
                f"`cancel {action.id}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def format_pending_action_detail(action_id: str) -> str:
    action = get_pending_action(action_id)
    if not action:
        return f"I could not find pending action `{action_id}`."
    lines = [
        "Pending action",
        "",
        f"ID: {action.id}",
        f"Status: {action.status}",
        f"Type: {action.action_type}",
        f"Risk: {action.risk_category} ({action.risk_level})",
        f"Summary: {action.summary}",
        f"Target: {action.target or 'not specified'}",
        f"Payload: {action.payload_summary or 'summary only'}",
        f"Source: {action.source}",
        f"Executor available: {'yes' if action.executor_available else 'no'}",
        f"Safety: {action.safety_reason or 'No extra safety note.'}",
        f"Expires: {action.expires_at}",
        "",
        "No real action has been executed from this pending record.",
    ]
    if action.status in {"pending_confirmation", "pending_override"}:
        command = f"confirm override {action.id}" if action.requires_override else f"confirm {action.id}"
        lines.extend(["", f"Say `{command}` to approve this exact action, or `cancel {action.id}` to cancel it."])
    return "\n".join(lines)


def format_permission_status() -> str:
    status = pending_action_ledger_status()
    counts = status.get("status_counts") if isinstance(status.get("status_counts"), dict) else {}
    active = int(counts.get("pending_confirmation", 0)) + int(counts.get("pending_override", 0))
    return "\n".join(
        [
            "Permissions status: Eva's pending-action ledger is active.",
            f"Active pending actions: {active}.",
            f"Pending confirmation: {counts.get('pending_confirmation', 0)}. Pending override: {counts.get('pending_override', 0)}.",
            "Confirmations must include an action ID, like `confirm act_abc123`.",
            "Overrides must use the exact form `confirm override act_abc123`.",
            "Confirmed risky actions still do not execute in this build; they are marked confirmed until a later verified executor phase.",
        ]
    )


def format_pending_action_result(result: EvaPendingActionResult) -> str:
    action = result.action
    if not action:
        return result.message
    lines = [result.message, "", "Pending action:", f"ID: {action.id}", f"Status: {action.status}", f"Risk: {action.risk_category}", f"Summary: {action.summary}"]
    if action.status == "confirmed_but_executor_unavailable":
        lines.extend(["", "Execution:", "No real action was executed. The verified executor for this action is not available in this phase."])
    return "\n".join(lines)
