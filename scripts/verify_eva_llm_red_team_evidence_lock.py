from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.llm.red_team_baseline import load_red_team_baseline
    from backend.eva.llm.red_team_cases import list_red_team_cases
    from backend.eva.llm.red_team_evidence_lock import build_evidence_lock_report, format_evidence_lock_report
    from backend.eva.llm.red_team_runner import RedTeamRun, run_local_red_team
    from scripts import verify_eva_all

    cases, baseline, run = list_red_team_cases(), load_red_team_baseline(), run_local_red_team()
    report = build_evidence_lock_report(run, baseline, cases)
    check(report.passed and report.total_cases == len(cases) and not report.live_calls_used and not report.tool_execution_used and not report.write_path_used, "baseline evidence lock failed")
    check(all(item.passed for item in report.entries), "baseline mismatch")
    check("no. Tool execution used: no" in format_evidence_lock_report(report), "unsafe report")
    check(not build_evidence_lock_report(run, baseline[:-1], cases).passed, "missing baseline accepted")
    unknown = baseline + (replace(baseline[0], case_id="unknown_case"),)
    check(not build_evidence_lock_report(run, unknown, cases).passed, "unknown baseline accepted")
    duplicate = baseline + (baseline[0],)
    check(not build_evidence_lock_report(run, duplicate, cases).passed, "duplicate baseline accepted")
    mismatched = (replace(baseline[0], expected_outcome="allowed"),) + baseline[1:]
    check(not build_evidence_lock_report(run, mismatched, cases).passed, "mismatch accepted")
    unsafe_run = RedTeamRun((replace(run.results[0], safe=False, outcome="allowed"),) + run.results[1:], run.total, run.failed_safely - 1, False, False)
    check(not build_evidence_lock_report(unsafe_run, baseline, cases).passed, "unsafe allow accepted")
    check("verify_eva_llm_red_team_evidence_lock.py" in verify_eva_all.FULL_VERIFIERS and "verify_eva_llm_red_team_evidence_lock.py" in verify_eva_all.QUICK_VERIFIERS, "master profile missing evidence lock")
    print("PASS: Phase 15E adversarial regression baseline and evidence lock are intact.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
