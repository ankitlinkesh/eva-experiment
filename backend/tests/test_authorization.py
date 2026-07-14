"""Executable spec for backend/eva/threat_defense/authorization.py (Phase 40a).

Fully offline and deterministic. Exercises the three canonical
``authorize_action`` cases: unprivileged content may always propose a bounded
read; a privileged action proposed under tainted, injected context must
escalate rather than auto-authorize; a privileged action with clean context is
left to the normal permission gate.
"""

from __future__ import annotations

from backend.eva.threat_defense.authorization import authorize_action


def test_unprivileged_tool_under_tainted_context_is_allowed():
    decision = authorize_action(tool_privileged=False, context_tainted=True, injection_detected=True)

    assert decision.allow is True
    assert decision.escalate is False
    assert decision.injection_suspected is False


def test_privileged_tool_under_tainted_injected_context_escalates():
    decision = authorize_action(tool_privileged=True, context_tainted=True, injection_detected=True)

    assert decision.escalate is True
    assert decision.injection_suspected is True
    assert decision.allow is False


def test_privileged_tool_with_clean_context_is_allowed():
    decision = authorize_action(tool_privileged=True, context_tainted=False, injection_detected=False)

    assert decision.allow is True
    assert decision.escalate is False


def test_as_dict_shape():
    decision = authorize_action(tool_privileged=True, context_tainted=True, injection_detected=True)
    payload = decision.as_dict()

    assert payload == {
        "allow": decision.allow,
        "escalate": decision.escalate,
        "injection_suspected": decision.injection_suspected,
        "reason": decision.reason,
    }
    assert isinstance(payload["reason"], str) and payload["reason"]
