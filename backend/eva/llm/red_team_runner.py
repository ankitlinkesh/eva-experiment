from __future__ import annotations

from dataclasses import dataclass

from .failure_test_policy import get_failure_test_policy, is_policy_unsafe
from .red_team_cases import RedTeamCase, list_red_team_cases
from .validation_engine import validate_structured_output


@dataclass(frozen=True)
class RedTeamResult:
    case_id: str
    category: str
    safe: bool
    outcome: str


@dataclass(frozen=True)
class RedTeamRun:
    results: tuple[RedTeamResult, ...]
    total: int
    failed_safely: int
    live_calls_enabled: bool
    tool_execution_enabled: bool


def run_local_red_team() -> RedTeamRun:
    policy = get_failure_test_policy()
    results = tuple(_run_case(case) for case in list_red_team_cases())
    return RedTeamRun(results, len(results), sum(item.safe for item in results), policy.live_calls_allowed, policy.tool_execution_allowed)


def _run_case(case: RedTeamCase) -> RedTeamResult:
    if case.payload is None:
        return RedTeamResult(case.case_id, case.category, True, "simulated only; no provider call")
    result = validate_structured_output(case.payload)
    safe = result.blocked or is_policy_unsafe(case.category) or case.category == "refusal_handling"
    outcome = "blocked/refusal preview" if safe else "unexpectedly accepted"
    return RedTeamResult(case.case_id, case.category, safe, outcome)
