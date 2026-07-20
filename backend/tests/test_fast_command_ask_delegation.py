"""Executable spec for the `eva ask` -> fast-command delegation path (Phase 71).

Phase 71 extracted _handle_eva_ask_command out of fast_commands.py into
fast_command_ask.py. fast_commands.py imports that module at the top level, so
the delegation call at the end of _handle_eva_ask_command --

    if route.suggested_command:
        from .fast_commands import maybe_handle_fast_command
        delegated = maybe_handle_fast_command(route.suggested_command, ...)

-- can no longer import maybe_handle_fast_command at module scope without a
circular import. It is deferred to call time instead.

That deferred import sits INSIDE a branch, which is exactly what makes it worth
pinning: a circular-import regression there is invisible to static analysis, and
at the time of the extraction NOTHING in the 96 verifiers or 771 tests entered
this branch -- the whole suite stayed green while the line was unproven. It had
to be reached by hand (an "eva ask " prefix, then a natural-language phrasing
whose intent is not intercepted by one of the ~160 earlier branches).

The failure this guards is silent, not loud, in one direction: if the delegated
call returns None the code falls back to "Suggested safe command: `...`" and
still produces a plausible-looking answer, so asserting only "a response came
back" would pass against a broken delegation. Both assertions below are
therefore required -- one proves the import executed, the other proves the
delegation actually returned content.
"""

from __future__ import annotations

from eva.core.fast_commands import maybe_handle_fast_command
from eva.tools.registry import ToolRegistry


def test_eva_ask_delegates_through_deferred_import() -> None:
    """`eva ask show roadmap status` routes to `eva roadmap status` and runs it.

    Reaching this branch requires all three: the "eva ask " prefix, a phrasing
    the natural router maps to a suggested_command, and an intent with no
    earlier handler. roadmap_status satisfies all three and is read-only.
    """
    result = maybe_handle_fast_command(
        "eva ask show roadmap status",
        ToolRegistry(),
        session_context={},
        memory=None,
        session_id="test-ask-delegation",
    )

    assert result is not None, "eva ask should be handled as a fast command"
    body, source = result
    assert source == "fast-command"

    # The router understood it and picked the delegate target.
    assert "roadmap_status" in body
    assert "eva roadmap status" in body

    # Delegation actually ran. If the deferred import were removed or the call
    # returned None, the handler would emit this fallback string instead of the
    # delegated command's own output.
    assert "Suggested safe command:" not in body, (
        "delegation returned None -- the fast-command fallback was used"
    )
    assert "Eva phase improvement roadmap" in body, (
        "the delegated `eva roadmap status` output is missing from the response"
    )
