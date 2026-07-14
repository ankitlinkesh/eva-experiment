"""Executable spec for Phase 39 reliability tracking.

Covers backend/eva/agent/state.py's AgentRunState (the failure/stall/success
bookkeeping the agent loop uses to recover from a single bad step instead of
dying on it) and backend/eva/agent/policies.py's budget getters
(max_consecutive_failures/max_steps_without_progress), including their
env-var overrides.
"""

from __future__ import annotations

from backend.eva.agent.policies import max_consecutive_failures, max_steps_without_progress
from backend.eva.agent.state import AgentRunState


def test_record_failure_increments_counters_and_sets_last_error():
    state = AgentRunState()

    state.record_failure("boom")

    assert state.consecutive_failures == 1
    assert state.failures == 1
    assert state.steps_since_progress == 1
    assert state.last_error == "boom"


def test_record_failure_accumulates_across_multiple_calls():
    state = AgentRunState()

    state.record_failure("first")
    state.record_failure("second")

    assert state.consecutive_failures == 2
    assert state.failures == 2
    assert state.steps_since_progress == 2
    assert state.last_error == "second"


def test_record_success_resets_failure_streak_and_stall_counter():
    state = AgentRunState()
    state.record_failure("boom")
    state.record_failure("boom again")

    state.record_success()

    assert state.consecutive_failures == 0
    assert state.steps_since_progress == 0
    assert state.successes == 1
    assert state.verified_successes == 0


def test_record_success_verified_increments_verified_successes():
    state = AgentRunState()

    state.record_success(verified=True)

    assert state.successes == 1
    assert state.verified_successes == 1

    state.record_success(verified=False)

    assert state.successes == 2
    assert state.verified_successes == 1


def test_failure_budget_exceeded_true_at_and_after_limit():
    state = AgentRunState()

    state.record_failure("one")
    assert state.failure_budget_exceeded(2) is False

    state.record_failure("two")
    assert state.failure_budget_exceeded(2) is True

    state.record_failure("three")
    assert state.failure_budget_exceeded(2) is True


def test_failure_budget_exceeded_false_after_a_success_resets_it():
    state = AgentRunState()
    state.record_failure("one")
    state.record_failure("two")
    assert state.failure_budget_exceeded(2) is True

    state.record_success()

    assert state.failure_budget_exceeded(2) is False


def test_stalled_true_at_and_after_limit():
    state = AgentRunState()

    state.record_failure("one")
    state.record_failure("two")
    assert state.stalled(3) is False

    state.record_failure("three")
    assert state.stalled(3) is True

    state.record_failure("four")
    assert state.stalled(3) is True


def test_max_consecutive_failures_default_is_two():
    assert max_consecutive_failures() == 2


def test_max_steps_without_progress_default_is_three():
    assert max_steps_without_progress() == 3


def test_max_consecutive_failures_honors_env_override(monkeypatch):
    monkeypatch.setenv("EVA_AGENT_MAX_CONSECUTIVE_FAILURES", "5")

    assert max_consecutive_failures() == 5


def test_max_steps_without_progress_honors_env_override(monkeypatch):
    monkeypatch.setenv("EVA_AGENT_MAX_STEPS_WITHOUT_PROGRESS", "7")

    assert max_steps_without_progress() == 7
