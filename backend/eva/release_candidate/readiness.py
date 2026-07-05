from __future__ import annotations


VERIFICATION_COMMANDS = (
    r".\.venv\Scripts\python.exe -m compileall backend scripts",
    r".\.venv\Scripts\python.exe scripts\verify_eva_release_candidate_hardening.py",
    r".\.venv\Scripts\python.exe scripts\verify_eva_all.py --list",
    r".\.venv\Scripts\python.exe scripts\verify_eva_all.py --quick --timeout 90",
    r".\.venv\Scripts\python.exe scripts\verify_eva_all.py --full --timeout 90",
    "git diff --check",
    "git status --short",
)


def readiness_text() -> str:
    return "\n".join(
        (
            "Eva Phase 30 release-candidate readiness",
            "- Final status: ready for user review, not committed or published.",
            "- Blocking issues: none after all documented checks pass.",
            "- Non-blocking warnings: ignored environment filenames and the intentionally dirty Phase 30 tree.",
            "- Documentation consistency: Phase 30 boundaries are aligned across public and internal status docs.",
            "- Safety boundary: unchanged; unsafe execution classes remain locked.",
            "- Safe to commit?: yes only after fresh verification and explicit user approval outside Eva.",
            "- Recommended next action: user-approved commit execution outside Eva or a separate explicit commit-approval phase.",
        )
    )


def verification_text() -> str:
    return "\n".join(
        (
            "Eva Phase 30 verification plan",
            "- Run manually from the repository root:",
            *(f"  - {command}" for command in VERIFICATION_COMMANDS),
            "- Eva does not execute these commands; fresh terminal evidence controls the readiness claim.",
        )
    )
