from __future__ import annotations

from dataclasses import dataclass

from .red_team_cases import list_red_team_cases


@dataclass(frozen=True)
class BaselineExpectation:
    case_id: str
    category: str
    expected_safe: bool
    expected_outcome: str


def load_red_team_baseline() -> tuple[BaselineExpectation, ...]:
    return tuple(
        BaselineExpectation(
            case.case_id,
            case.category,
            True,
            "simulated only; no provider call" if case.payload is None else "blocked/refusal preview",
        )
        for case in list_red_team_cases()
    )
