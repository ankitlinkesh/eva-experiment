"""Standalone verifier for Phase 80 (gate agreement + preview separation).

Two gates enforce on two paths and both map an ``action_type`` to hard_block /
override / confirm / allow: ``permission_gate.evaluate_action`` (action path)
and ``tool_gate.classify_tool_call`` (tool-call path). They read different
per-object fields, which is correct, but the action-type TAXONOMY they share
must agree -- otherwise the same action is gated one way as a tool and another
as an action. The ``OVERRIDE``/``CONFIRM`` sets used to be re-declared as
separate-but-identical literals in each gate; a single edit to one could drift
them (the Phase 78 shape). This phase single-sources the sets and pins the
agreement so drift becomes impossible-by-construction plus caught-if-attempted.

A third classifier, ``execution_gates.action_classifier``, is a report-only
string-policy PREVIEW over free text -- not an enforcement gate. The last check
pins that neither enforcement gate consumes it, so a preview that disagrees with
enforcement can only mislead a human, never gate execution.

What this verifies:

  1. THE SETS ARE ONE OBJECT. tool_gate's OVERRIDE/CONFIRM ARE the permission
     gate's, so they cannot drift.
  2. THE GATES AGREE on every classified ActionType (both produce the class the
     shared taxonomy says).
  3. EVERY TYPE IS ACCOUNTED FOR -- classified, or the single documented gap.
  4. THE ONE DIVERGENCE (UNKNOWN default: confirm vs allow) is explicit and
     safe only because Phase 51 guarantees no registered tool is UNKNOWN.
  5. THE PREVIEW CLASSIFIER NEVER GATES: no enforcement gate references it.

Fully offline: pure classification of bare action/spec objects, no gate side
effects, no network.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


_PG_DECISION_TO_CLASS = {
    "hard_block": "hard_block",
    "ask_override": "override",
    "ask_confirmation": "confirm",
    "allow": "allow",
}


def main() -> int:
    from eva.security import permission_gate, tool_gate
    from eva.security.action_types import ActionType
    from eva.security.permission_gate import (
        ALLOW,
        CONFIRM,
        HARD_BLOCK,
        OVERRIDE,
        PermissionContext,
        evaluate_action,
    )
    from eva.security.tool_gate import CONFIRM_ACTION_TYPES, OVERRIDE_ACTION_TYPES, classify_tool_call

    def pg_class(action_type: str) -> str:
        decision = evaluate_action(SimpleNamespace(action_type=action_type), PermissionContext())
        return _PG_DECISION_TO_CLASS[decision.decision]

    def tg_class(action_type: str) -> str:
        return classify_tool_call(SimpleNamespace(action_type=action_type))

    def expected_class(action_type: str) -> str | None:
        if action_type == ActionType.SHELL_ACTION.value or action_type in HARD_BLOCK:
            return "hard_block"
        if action_type in OVERRIDE:
            return "override"
        if action_type in CONFIRM:
            return "confirm"
        if action_type in ALLOW:
            return "allow"
        return None

    # ------------------------------------------------------------------ 1
    check(OVERRIDE_ACTION_TYPES is OVERRIDE, "tool_gate OVERRIDE is a separate object from permission_gate OVERRIDE -- they can drift")
    check(CONFIRM_ACTION_TYPES is CONFIRM, "tool_gate CONFIRM is a separate object from permission_gate CONFIRM -- they can drift")

    # ------------------------------------------------------------------ 2 + 3
    classified = 0
    for action_type in ActionType:
        expected = expected_class(action_type.value)
        if expected is None:
            check(
                action_type is ActionType.UNKNOWN_RISK,
                f"{action_type.value} is unclassified but is not the documented UNKNOWN_RISK gap",
            )
            continue
        classified += 1
        check(pg_class(action_type.value) == expected, f"permission gate disagrees on {action_type.value}: {pg_class(action_type.value)} != {expected}")
        check(tg_class(action_type.value) == expected, f"tool gate disagrees on {action_type.value}: {tg_class(action_type.value)} != {expected}")
    check(classified >= 16, f"only {classified} action types were classified; the taxonomy shrank unexpectedly")

    # ------------------------------------------------------------------ 4
    check(pg_class(ActionType.UNKNOWN_RISK.value) == "confirm", "the action gate no longer defaults UNKNOWN to confirm")
    check(tg_class(ActionType.UNKNOWN_RISK.value) == "allow", "the tool gate no longer defaults UNKNOWN to allow (Phase 51 keeps this safe)")

    # ------------------------------------------------------------------ 5
    for module in (permission_gate, tool_gate):
        source = Path(module.__file__).read_text(encoding="utf-8")
        check("execution_gates" not in source, f"{module.__name__} references the preview classifier -- a preview could start gating execution")

    # ------------------------------------------------------------------ registration
    import verify_eva_all

    name = "verify_eva_phase80_gate_agreement.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 80 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 80 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 80 verifier")

    print(
        "PASS: Phase 80 gate agreement. The two enforcement gates -- permission_gate.evaluate_action (action path) and "
        "tool_gate.classify_tool_call (tool-call path) -- map an action_type to the same four classes. Their OVERRIDE "
        "and CONFIRM sets used to be separate-but-identical literals that could drift the moment one was edited; they "
        "are now the SAME objects (single-sourced in the permission gate), and every classified ActionType is proven to "
        "receive the same class from both gates, with every type accounted for. The one deliberate divergence -- an "
        "UNKNOWN action_type defaults to confirm on the action path and allow on the tool path -- is pinned as "
        "intentional and safe only because Phase 51 guarantees no registered tool is UNKNOWN. The third classifier, the "
        "execution_gates preview, is report-only string policy; neither enforcement gate references it, so a preview "
        "that disagrees with reality can mislead a human but never gate execution."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
