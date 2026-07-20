"""The currently-active delegated role (Phase 72).

WHY THIS IS AMBIENT AND NOT AN ARGUMENT -- the load-bearing design decision:

`registry.run` strips `confirmed`, `_approved` and `content_args` from caller
kwargs, because each is a signal that REDUCES friction and so must never come
from the caller. The active role is the same kind of signal in reverse: it
constrains what may be called, so a caller able to CHOOSE its own role could
simply claim whichever role unlocks the tool it wants. Injected page content
asking to "switch to the desktop role" would then be self-authorization.

So the role is ambient state, set only by the delegation boundary in source
(see `role_scope`), never read from tool arguments. `registry.run` additionally
strips any caller-supplied `role`/`_role`/`agent_role` kwarg for the same reason
it strips `confirmed`.

NO ACTIVE ROLE MEANS NO ROLE RESTRICTION. Ordinary typed-console and planner
calls run with no role set and are completely unaffected by Phase 72 -- this
module adds a constraint inside delegated sub-tasks, it does not re-gate the
existing product. Untrusted content cannot clear the role either: it is set and
reset by `role_scope` around the sub-task, not by anything the model emits.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

_active_role: ContextVar[str | None] = ContextVar("eva_active_agent_role", default=None)

# Caller-supplied spellings that must never be honoured as a role declaration.
ROLE_KWARG_NAMES = frozenset({"role", "_role", "agent_role"})


def active_role() -> str | None:
    """The role of the sub-task currently executing, or None at top level."""
    return _active_role.get()


def set_active_role(role: str | None) -> Token:
    return _active_role.set(role)


def reset_active_role(token: Token) -> None:
    _active_role.reset(token)


@contextmanager
def role_scope(role: str | None) -> Iterator[str | None]:
    """Run a delegated sub-task under `role`.

    The reset is in a `finally` so a raising sub-task cannot leak its role to
    the caller -- a leaked role would silently restrict subsequent top-level
    calls, which fails safe, but a leaked role after an EXCEPTION is exactly the
    confusing state that makes such a bug hard to find.
    """
    token = _active_role.set(role)
    try:
        yield role
    finally:
        _active_role.reset(token)
