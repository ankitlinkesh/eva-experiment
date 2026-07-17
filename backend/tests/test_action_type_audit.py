"""The auto-allow audit (Phase 51).

Both screen bypasses had one root cause: omit ``action_type`` on a ToolSpec and
it silently inherits ``SAFE_LOCAL_READ``, which is ALLOW-class. The dangerous
default is the *invisible* one — nothing failed, nothing warned, the tool just
ran unguarded. These tests make that impossible to reintroduce quietly.
"""

from __future__ import annotations

import pytest

from eva.security import tool_gate
from eva.security.action_audit import (
    AUDITED_SAFE_LOCAL_READ,
    LOCAL_WRITE_TOOLS,
    NETWORK_TOOLS,
    unaudited_safe_local_reads,
)
from eva.security.action_types import ActionType
from eva.tools.registry import ToolRegistry


@pytest.fixture()
def registry():
    return ToolRegistry()


def test_no_tool_is_auto_allowed_without_review(registry):
    """THE GUARD: a new tool that forgets action_type must fail here rather than
    silently become unguarded."""
    offenders = unaudited_safe_local_reads(registry._tools)
    assert offenders == [], (
        f"{offenders} are auto-allowed (SAFE_LOCAL_READ) but unreviewed. Declare an honest action_type, "
        "or add them to AUDITED_SAFE_LOCAL_READ with a reason."
    )


def test_the_guard_actually_catches_an_unreviewed_tool(registry):
    """Prove the guard bites — a guard that never fires protects nothing."""

    class _Spec:
        action_type = "SAFE_LOCAL_READ"

    tools = dict(registry._tools)
    tools["sneaky_new_tool"] = _Spec()
    assert "sneaky_new_tool" in unaudited_safe_local_reads(tools)


def test_every_action_type_is_real(registry):
    """A typo'd action_type is not a new class — it is auto-allow."""
    valid = {t.value for t in ActionType}
    for name, spec in registry._tools.items():
        assert spec.action_type in valid, f"{name} has a bogus action_type {spec.action_type!r}"


def test_network_tools_do_not_claim_to_be_local_reads(registry):
    for name in NETWORK_TOOLS:
        spec = registry.get(name)
        if spec is None:
            continue
        assert spec.action_type != "SAFE_LOCAL_READ", f"{name} reaches the network"


def test_local_writes_do_not_claim_to_be_reads(registry):
    for name in LOCAL_WRITE_TOOLS:
        spec = registry.get(name)
        if spec is None:
            continue
        assert spec.action_type != "SAFE_LOCAL_READ", f"{name} writes local state"


def test_audited_list_never_launders_a_pixel_grabber(registry):
    for name in ("capture_screen", "analyze_screen", "screen.observe"):
        assert name not in AUDITED_SAFE_LOCAL_READ, f"{name} captures pixels and must never be auto-allowed"


def test_audited_tools_really_are_allow_class(registry):
    for name in AUDITED_SAFE_LOCAL_READ:
        spec = registry.get(name)
        if spec is None:
            continue
        assert tool_gate.classify_tool_call(spec) == "allow", f"{name} is on the auto-allow list but is not allow-class"


def test_relabelling_is_gate_preserving(registry):
    """Honest metadata must not have loosened (or tightened) the gate."""
    counts: dict[str, int] = {}
    for spec in registry._tools.values():
        cls = tool_gate.classify_tool_call(spec)
        counts[cls] = counts.get(cls, 0) + 1
    assert counts == {"allow": 84, "override": 12, "confirm": 7}, f"gate class counts drifted: {counts}"
