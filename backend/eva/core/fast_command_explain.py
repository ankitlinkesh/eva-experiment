"""Typed-console entry for explaining a pending action (Phase 75).

    explain act_e8517efcb48c
    explain                     (the most recent pending action)

DISPATCHER SHADOWING -- why this matches so narrowly:

`maybe_handle_fast_command` matches prefixes IN ORDER, and two later branches
already own `explain feature <x>` and `explain project architecture`. A bare
`explain ` prefix inserted ahead of them would silently capture both, which is
the failure Phase 71 was scoped around: an earlier branch shadowing a later one
changes which command wins, and no test would notice because both still return
a plausible answer.

So this handler claims `explain` ONLY when the remainder is a pending-action id
(`act_...`), or when it is bare AND a pending action actually exists. In every
other case it returns None and the existing branches keep their meaning.
"""

from __future__ import annotations

from typing import Any

from ..mcp.runner import run_async
from .fast_command_helpers import _after_prefix


def _explain_pending(action: Any, tools: Any) -> str:
    from ..agents.explainer import explain_action, generate_explanation

    tool_name = str(getattr(action, "action_type", "") or "")
    # Prefer the live spec's description over the stored summary: the summary is
    # a formatted string, the spec is the source of truth.
    description = ""
    spec = getattr(tools, "_tools", {}).get(tool_name)
    if spec is not None:
        description = str(getattr(spec, "description", "") or "")
    if not description:
        description = str(getattr(action, "summary", "") or "")

    decision = "override" if getattr(action, "requires_override", False) else "confirm"

    explanation = explain_action(
        tool=tool_name,
        description=description,
        action_type=str(getattr(action, "risk_category", "") or "UNKNOWN_RISK"),
        decision=decision,
        # The MASKED payload. An explanation must never be the thing that
        # prints a value the ledger deliberately hid.
        args=dict(getattr(action, "redacted_payload", None) or {}),
    )
    explanation = run_async(generate_explanation(explanation))
    return explanation.as_text()


def _handle_explain_command(
    normalized: str,
    original: str,
    tools: Any,
    session_context: dict | None,
    memory: object | None,
    session_id: str | None,
) -> tuple[str, str] | None:
    from ..permissions.ledger import get_pending_action, list_pending_actions

    request = _after_prefix(original, ("explain ",))
    if request:
        action_id = request.strip()
        if not action_id.startswith("act_"):
            # Not ours -- let `explain feature ...` and friends keep working.
            return None
        action = get_pending_action(action_id)
        if action is None:
            return f"No pending action `{action_id}`. It may have expired or already run.", "fast-command"
        return _explain_pending(action, tools), "fast-command"

    if normalized == "explain":
        pending = list_pending_actions(limit=1)
        if not pending:
            return None  # nothing to explain; fall through
        return _explain_pending(pending[0], tools), "fast-command"

    return None
