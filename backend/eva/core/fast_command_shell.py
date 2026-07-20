"""Typed-console entry for the bounded command runner (Phase 74).

    $ git status
    $ git log -n 5
    bounded commands

WHY `$ ` AND NOT `run `: the dispatcher matches prefixes in order, so a prefix
that occurs in ordinary prose would silently start handling requests that
should reach the LLM -- "run a search for X" would be parsed as the command
`a`. A refactor that STARTS handling a phrase is as much a regression as one
that stops (Phase 71), so the prefix is deliberately one that cannot appear in
a normal sentence.

WHY THIS GOES THROUGH registry.run RATHER THAN CALLING THE RUNNER DIRECTLY:
the tool is override-class, and routing the console path through the gate is
what keeps that meaningful. Calling `run_bounded` straight from here would work
and would be more convenient, and would also establish that the console is a
way around the gate -- which is exactly the property that must not exist.
"""

from __future__ import annotations

from typing import Any

from ..shell.bounded_runner import describe_allowed
from .fast_command_helpers import _after_prefix


def _handle_shell_command(
    normalized: str,
    original: str,
    tools: Any,
    session_context: dict | None,
    memory: object | None,
    session_id: str | None,
) -> tuple[str, str] | None:
    if normalized in {"bounded commands", "shell commands", "allowed commands"}:
        return describe_allowed(), "fast-command"

    request = _after_prefix(original, ("$ ", "$"))
    if not request:
        return None

    parts = request.split()
    if not parts:
        return (
            "Usage: $ <command> [args]\n\nSee `bounded commands` for what is allowed.",
            "fast-command",
        )

    # Check the allowlist BEFORE the gate. `validate` is pure, so this costs
    # nothing and weakens nothing -- run_bounded validates again at execution,
    # and this is only a pre-filter. Without it the gate parks `$ git push` for
    # confirmation and only refuses it afterwards, which asks the user to
    # approve something that can never run and leaves a pending action in the
    # ledger for every typo.
    from ..shell.bounded_runner import validate

    refusal = validate(parts[0], tuple(parts[1:]))
    if refusal:
        return f"$ {request}\n\nRefused: {refusal}", "fast-command"

    result = tools.run("shell.run_bounded", command=parts[0], args=parts[1:])

    if isinstance(result, dict):
        # The gate parked it for confirmation rather than running it.
        if result.get("pending_id") or result.get("requires_confirmation") or result.get("requires_override"):
            return (
                f"`{request}` needs confirmation before it runs.\n\n"
                f"{result.get('message') or 'Confirm the pending action to proceed.'}",
                "fast-command",
            )
        if result.get("role_denied"):
            return str(result.get("message") or "Refused by role policy."), "fast-command"
        text = result.get("text")
        if text:
            return str(text), "fast-command"
        return str(result.get("error") or "The command produced no result."), "fast-command"

    return str(result), "fast-command"
