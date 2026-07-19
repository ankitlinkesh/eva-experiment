"""Executable spec for backend/eva/runtime/nodes.py::verify_node (Phase 69).

Confirmed defect: the `elif state.execution_summary:` branch claimed
verified=True, confidence=0.76 from nothing more than "execution_summary is a
non-empty string" -- and execution_bridge.py's `_run_browser_open_action`
path populates execution_summary with a non-empty message REGARDLESS of
whether the open actually succeeded (`_clean_result_message(result,
fallback=...)`), so a genuinely FAILED browser-open was being reported
verified=True. This is the same self-report-laundering shape Phase 64 fixed
in tools/postconditions.py, live in the v2_execute runtime path (not
dormant -- this branch runs whenever v2_execute mode is used).

Also covers the neighboring execution_refused_reason branch: it used to
assert "before any tool ran" unconditionally, which is false when a
read-only delegate actually ran and reported it could not complete
(execution_bridge._run_readonly_delegate sets execution_refused_reason in
that case too, with executed_by/executed_actions populated).
"""

from __future__ import annotations

from backend.eva.runtime.nodes import verify_node
from backend.eva.runtime.state import EvaRuntimeState


def _state(**overrides) -> EvaRuntimeState:
    state = EvaRuntimeState(user_request="do a thing")
    state.execution_mode = "v2_execute"
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def test_successful_execution_summary_is_self_reported_not_a_fabricated_high_confidence():
    state = _state(
        execution_summary="Requested Chrome open for gmail.",
        executed_actions=[{"action_type": "browser.open_public_webapp", "status": "executed", "summary": "ok"}],
    )

    result_state = verify_node(state)

    result = result_state.verification_results[-1]
    assert result["verified"] is True
    assert result["provenance"] == "self_reported"
    assert result["independent"] is False
    assert result["confidence"] < 0.76, "must not keep the old fabricated flat confidence"


def test_failed_browser_open_with_nonempty_summary_is_no_longer_falsely_verified():
    """The concrete regression: _run_browser_open_action populates
    execution_summary even when ok=False, marking the executed_actions entry
    "attempted_unverified" instead of "executed". Before Phase 69 this still
    hit the `elif state.execution_summary:` branch and came back
    verified=True, confidence=0.76 -- a lie."""
    state = _state(
        execution_summary="Requested Chrome open for gmail.",
        executed_actions=[{"action_type": "browser.open_public_webapp", "status": "attempted_unverified", "summary": "failed"}],
    )

    result_state = verify_node(state)

    result = result_state.verification_results[-1]
    assert result["verified"] is False, f"a failed open must not be reported verified=True: {result}"
    assert result["provenance"] == "self_reported"


def test_execution_refused_before_anything_ran_is_independent_and_verified():
    state = _state(execution_refused_reason="blocked by policy")

    result_state = verify_node(state)

    result = result_state.verification_results[-1]
    assert result["verified"] is True
    assert result["provenance"] == "independent"
    assert result["independent"] is True


def test_execution_refused_after_a_readonly_delegate_attempted_is_not_claimed_unattempted():
    """executed_by is set by _run_readonly_delegate BEFORE the `if not ok`
    branch sets execution_refused_reason -- so this state combination is
    real, not synthetic. Must not claim "before any tool ran" when a
    delegate demonstrably ran."""
    state = _state(
        execution_refused_reason="the memory delegate could not answer",
        executed_by="v2_read_only_delegate:memory",
        executed_actions=[{"action_type": "memory.read", "status": "unavailable"}],
    )

    result_state = verify_node(state)

    result = result_state.verification_results[-1]
    assert "before any tool ran" not in result["evidence"], f"a delegate demonstrably ran: {result}"
    assert result["provenance"] == "self_reported"
    assert result["verified"] is False, "the task did not complete; this must not be reported as verified success"


def test_missing_execution_summary_is_still_unverified():
    state = _state()

    result_state = verify_node(state)

    result = result_state.verification_results[-1]
    assert result["verified"] is False
    assert result["failure_reason"] == "missing_execution_summary"
