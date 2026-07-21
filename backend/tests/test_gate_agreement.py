"""Executable spec for gate agreement (Phase 80).

Two gates enforce, on two paths: ``permission_gate.evaluate_action`` on the
action path (routes, messaging, desktop-control), ``tool_gate.classify_tool_call``
on the tool-call path (registry.run, the agent runner). Both map an
``action_type`` to one of hard_block / override / confirm / allow. They read
different per-object fields (the action gate looks at destructive/privacy/
external flags; the tool gate at safety_level/requires_confirmation), which is
correct -- but the ACTION-TYPE TAXONOMY they share must agree, or the same
action would be gated one way as a tool and another way as an action.

Historically ``OVERRIDE``/``CONFIRM`` were re-declared as separate literals in
each gate that merely happened to be identical -- exactly the unpinned
cross-component invariant Phase 78 was about. Phase 80 makes them the SAME
objects (single source in the permission gate) and pins the agreement here so a
future edit cannot reintroduce drift.

A third classifier, ``execution_gates.action_classifier``, is deliberately NOT
part of this: it is a report-only string-policy PREVIEW over free text, not an
enforcement gate. The last test pins that the enforcement gates never consume
it, so a preview that disagrees with enforcement can only ever mislead a human,
never gate execution.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from eva.security.action_types import ActionType
from eva.security.permission_gate import ALLOW, CONFIRM, HARD_BLOCK, OVERRIDE, PermissionContext, evaluate_action
from eva.security.tool_gate import CONFIRM_ACTION_TYPES, OVERRIDE_ACTION_TYPES, classify_tool_call
from eva.security import tool_gate, permission_gate

_PG_DECISION_TO_CLASS = {
    "hard_block": "hard_block",
    "ask_override": "override",
    "ask_confirmation": "confirm",
    "allow": "allow",
}


def _pg_class(action_type: str) -> str:
    """The permission gate's class for a BARE action of this type -- no
    destructive/privacy/external flags, so only the action_type taxonomy speaks."""
    decision = evaluate_action(SimpleNamespace(action_type=action_type), PermissionContext())
    return _PG_DECISION_TO_CLASS[decision.decision]


def _tg_class(action_type: str) -> str:
    return classify_tool_call(SimpleNamespace(action_type=action_type))


def _expected_class(action_type: str) -> str | None:
    if action_type == ActionType.SHELL_ACTION.value or action_type in HARD_BLOCK:
        return "hard_block"
    if action_type in OVERRIDE:
        return "override"
    if action_type in CONFIRM:
        return "confirm"
    if action_type in ALLOW:
        return "allow"
    return None  # unclassified (UNKNOWN_RISK) -- see the divergence test


class TestSetsAreSingleSourced:
    def test_override_is_the_same_object_in_both_gates(self) -> None:
        assert OVERRIDE_ACTION_TYPES is OVERRIDE

    def test_confirm_is_the_same_object_in_both_gates(self) -> None:
        assert CONFIRM_ACTION_TYPES is CONFIRM


class TestGatesAgreeOnEveryClassifiedType:
    def test_both_gates_match_the_shared_taxonomy(self) -> None:
        for action_type in ActionType:
            expected = _expected_class(action_type.value)
            if expected is None:
                continue
            assert _pg_class(action_type.value) == expected, f"permission gate disagrees on {action_type.value}"
            assert _tg_class(action_type.value) == expected, f"tool gate disagrees on {action_type.value}"

    def test_every_type_is_covered_by_one_side_or_the_documented_gap(self) -> None:
        """No ActionType silently falls outside the analysis: it is either
        classified (and pinned above) or the one known unclassified type."""
        for action_type in ActionType:
            if _expected_class(action_type.value) is None:
                assert action_type is ActionType.UNKNOWN_RISK, (
                    f"{action_type.value} is unclassified but is not the documented UNKNOWN_RISK gap"
                )


class TestTheOneDeliberateDivergence:
    def test_unknown_type_defaults_differ_and_that_is_intended(self) -> None:
        """An UNKNOWN action_type defaults to confirm on the action path but
        allow on the tool path. That is safe ONLY because the Phase 51 audit
        guarantees no registered tool is UNKNOWN_RISK -- the tool gate never
        actually sees one. Pinned so the divergence stays visible and any change
        to either default is a conscious one."""
        assert _pg_class(ActionType.UNKNOWN_RISK.value) == "confirm"
        assert _tg_class(ActionType.UNKNOWN_RISK.value) == "allow"


class TestPreviewClassifierNeverGatesExecution:
    def test_enforcement_gates_do_not_import_the_preview_classifier(self) -> None:
        """The execution_gates preview is report-only string policy. If an
        enforcement gate ever consumed it, a preview that disagrees with reality
        would start gating execution -- so neither gate may reference it."""
        for module in (permission_gate, tool_gate):
            source = Path(module.__file__).read_text(encoding="utf-8")
            assert "execution_gates" not in source, f"{module.__name__} references the preview classifier"
