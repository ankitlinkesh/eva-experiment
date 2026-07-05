from __future__ import annotations

from dataclasses import dataclass

from .red_team_baseline import BaselineExpectation, load_red_team_baseline
from .red_team_cases import RedTeamCase, list_red_team_cases
from .red_team_runner import RedTeamRun, run_local_red_team


@dataclass(frozen=True)
class EvidenceLockEntry:
    case_id: str
    category: str
    expected_outcome: str
    actual_outcome: str
    passed: bool
    failure_reason: str = ""


@dataclass(frozen=True)
class EvidenceLockReport:
    entries: tuple[EvidenceLockEntry, ...]
    total_cases: int
    passed: bool
    live_calls_used: bool
    tool_execution_used: bool
    write_path_used: bool


def build_evidence_lock_report(
    run: RedTeamRun | None = None,
    baseline: tuple[BaselineExpectation, ...] | None = None,
    cases: tuple[RedTeamCase, ...] | None = None,
) -> EvidenceLockReport:
    run = run or run_local_red_team()
    baseline = baseline or load_red_team_baseline()
    cases = cases or list_red_team_cases()
    case_ids = [item.case_id for item in cases]
    expected_ids = [item.case_id for item in baseline]
    duplicate_cases = {item for item in case_ids if case_ids.count(item) > 1}
    duplicate_baseline = {item for item in expected_ids if expected_ids.count(item) > 1}
    results = {item.case_id: item for item in run.results}
    expectations = {item.case_id: item for item in baseline}
    entries: list[EvidenceLockEntry] = []
    for case in cases:
        expected = expectations.get(case.case_id)
        actual = results.get(case.case_id)
        reason = ""
        if case.case_id in duplicate_cases:
            reason = "duplicate_case_id"
        elif case.case_id not in expectations:
            reason = "missing_baseline_entry"
        elif case.case_id in duplicate_baseline:
            reason = "duplicate_baseline_entry"
        elif actual is None:
            reason = "missing_runner_result"
        elif not actual.safe:
            reason = "unsafe_allow_result"
        elif actual.safe != expected.expected_safe or actual.outcome != expected.expected_outcome:
            reason = "baseline_mismatch"
        entries.append(EvidenceLockEntry(case.case_id, case.category, expected.expected_outcome if expected else "missing", actual.outcome if actual else "missing", not reason, reason))
    for case_id in set(expected_ids) - set(case_ids):
        entries.append(EvidenceLockEntry(case_id, "unknown", "locked", "missing", False, "unknown_baseline_entry"))
    passed = all(item.passed for item in entries) and not run.live_calls_enabled and not run.tool_execution_enabled
    return EvidenceLockReport(tuple(entries), len(entries), passed, run.live_calls_enabled, run.tool_execution_enabled, False)


def format_evidence_lock_report(report: EvidenceLockReport) -> str:
    failures = [item for item in report.entries if not item.passed]
    return "\n".join(["LLM Red-Team Evidence Lock", "", f"Cases checked: {report.total_cases}.", f"Result: {'locked' if report.passed else 'mismatch detected'}.", f"Mismatches: {len(failures)}.", "Live calls used: no. Tool execution used: no. New write path used: no."])
