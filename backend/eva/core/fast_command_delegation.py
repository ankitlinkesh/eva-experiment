"""Typed-console entry points for role-scoped delegation (Phase 73).

    delegate research: what changed in the LLM rate limits this week
    roles
    role research

WHY THIS IS CONSOLE-ONLY AND NOT A PLANNER TOOL:

Delegation itself only ever NARROWS capability -- a sub-task can do strictly
less than its parent -- so letting the planner delegate would not be an
escalation. The danger is upstream of that: whoever chooses the role and writes
the goal decides what the sub-task goes and does. If untrusted content could
reach that choice, it could stand up a sub-task pointed wherever it liked and
then feed the result back. So the choice stays with the person typing, exactly
as rule creation does (Phase 54) and form filling does (Phase 58).

The sub-task's OUTPUT is likewise data, not instruction: `DelegatedResult`
marks it untrusted and the console prints it as a report. Nothing here routes a
child's summary back into a planner.
"""

from __future__ import annotations

from typing import Any

from ..agents.delegation_runner import run_delegated
from ..agents.role_policy import describe_role, known_roles
from ..mcp.runner import run_async
from .fast_command_helpers import _after_prefix


def _format_roles() -> str:
    from ..agents.role_policy import ROLE_POLICIES

    lines = ["Delegation roles", ""]
    for name in known_roles():
        policy = ROLE_POLICIES[name]
        lines.append(f"- {name}: {policy.description}")
    lines += [
        "",
        "A sub-task may use only what its role allows; everything else is refused",
        "before it runs. Nesting only ever narrows further.",
        "",
        "Usage: delegate <role>: <goal>    Details: role <name>",
    ]
    return "\n".join(lines)


def _handle_delegation_command(
    normalized: str,
    original: str,
    tools: Any,
    session_context: dict | None,
    memory: object | None,
    session_id: str | None,
) -> tuple[str, str] | None:
    """Handle `roles`, `role <name>` and `delegate <role>: <goal>`."""
    if normalized in {"roles", "list roles", "delegation roles"}:
        return _format_roles(), "fast-command"

    role_query = _after_prefix(original, ("role ",))
    if role_query and normalized.startswith("role "):
        return describe_role(role_query.strip()), "fast-command"

    # Everything after the word "delegate" (may begin with ":" or a space, or be
    # empty). Handled here rather than via _after_prefix so that "delegate: goal"
    # (advisor, no space after the word) is recognised alongside "delegate goal".
    if normalized != "delegate" and not normalized.startswith(("delegate:", "delegate ")):
        return None
    remainder = original.strip()[len("delegate"):]
    role, separator, goal = remainder.partition(":")
    role = role.strip()
    goal = goal.strip()

    # Phase 79 role advisor: no explicit role means "suggest one". `delegate:
    # <goal>` (empty role before the colon) or `delegate <goal>` (no colon) asks
    # the specialists which role fits and which skills it can run, then prints
    # the exact command -- it never spawns a sub-task, so the person still picks
    # the role and confirms (the Phase 73 trust boundary). A bare `delegate`
    # lists the roles.
    if role == "":
        if not separator and not goal:
            return _format_roles(), "fast-command"
        return _advise(goal), "fast-command"
    if not separator:
        # `delegate <text>` with no colon and text that is not a bare role: treat
        # the text as a goal to advise on. (A known role with no goal falls through
        # to the advisor too, which will simply recommend that same role.)
        return _advise(role), "fast-command"

    context = {
        "registry": tools,
        "memory": memory,
        "session_id": session_id,
        "session_context": session_context,
    }
    result = run_async(run_delegated(role, goal, context))
    return result.as_text(), "fast-command"


def _advise(goal: str) -> str:
    from ..agents.role_advisor import advise

    return advise(goal).as_text()
