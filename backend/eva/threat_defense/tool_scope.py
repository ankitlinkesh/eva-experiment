"""Least-privilege per-task tool scoping (Phase 40c).

The permission gate governs *how dangerous* a tool is; taint tracking governs
*who motivated* a call. This adds the third least-privilege axis: *which tools
is this particular task even allowed to touch?* A task to "summarize my notes"
has no business calling ``file.delete`` — so a caller can hand the agent loop a
scope, and any planned tool outside it is denied before it runs, no matter what
the planner proposed.

Backward-compatible by design: when no scope is set the task is unrestricted
(today's behavior). A scope is opt-in least-privilege — the smaller the scope,
the less an injected or confused planner can reach. Matching supports exact tool
names and simple ``prefix.*`` / ``prefix_*`` wildcards so a task can be scoped
to a whole family (e.g. ``web.*`` read tools) without listing each one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskToolScope:
    """An allowlist of tools a single task may execute.

    ``patterns`` are exact tool names or ``prefix*`` wildcards. An empty scope
    means *unrestricted* (backward compatible) — use an explicit set to lock a
    task down. ``restricted`` distinguishes "no scope given" from "deliberately
    empty allowlist" so a caller can express "this task may run nothing".
    """

    patterns: frozenset[str]
    restricted: bool = True

    @classmethod
    def unrestricted(cls) -> "TaskToolScope":
        return cls(patterns=frozenset(), restricted=False)

    @classmethod
    def of(cls, tools: object) -> "TaskToolScope":
        """Build a scope from a list/set/str of tool names or wildcards.

        ``None`` yields an unrestricted scope; anything else yields a restricted
        allowlist (an empty iterable means "allow nothing").
        """
        if tools is None:
            return cls.unrestricted()
        if isinstance(tools, str):
            items = [tools]
        else:
            try:
                items = [str(item).strip() for item in tools if str(item).strip()]
            except TypeError:
                return cls.unrestricted()
        return cls(patterns=frozenset(items), restricted=True)

    def is_allowed(self, tool_name: str) -> bool:
        """Whether ``tool_name`` is permitted under this scope. Fail-safe: an
        unrestricted scope allows everything; a restricted scope allows only
        exact or wildcard-prefix matches."""
        if not self.restricted:
            return True
        name = str(tool_name or "")
        for pattern in self.patterns:
            if pattern == name:
                return True
            if pattern.endswith("*") and name.startswith(pattern[:-1]):
                return True
        return False
