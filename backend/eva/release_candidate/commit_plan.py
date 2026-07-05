from __future__ import annotations


COMMIT_GROUPING_PLAN = (
    "Review group 1 — core safety and execution gates.",
    "Review group 2 — browser and desktop observation/control-gate foundations.",
    "Review group 3 — voice, news, coding, public-demo, and release-candidate modules.",
    "Review group 4 — public documentation, safety proof, limitations, and release material.",
    "Review group 5 — focused verifiers and master verifier registration.",
)

PRE_COMMIT_CHECKLIST = (
    "Confirm the user intends to commit the complete interdependent checkpoint.",
    "Run compileall, the focused Phase 30 verifier, and master quick/full profiles.",
    "Run git diff --check and review git status without staging.",
    "Confirm ignored environment filenames remain excluded and their contents remain unread.",
    "Confirm no safety lock or Phase 12L write boundary changed.",
)

SUGGESTED_MESSAGES = (
    "Recommended checkpoint: Add Phase 30 release candidate hardening",
    "Optional split 1: Add deterministic release candidate reports",
    "Optional split 2: Integrate release candidate status surfaces",
    "Optional split 3: Document and verify release candidate boundaries",
)


def commit_plan_text() -> str:
    lines = (
        "Eva Phase 30 commit plan",
        "- Recommendation: use one user-approved checkpoint commit because code, docs, and verifiers are interdependent.",
        "- Logical review groups:",
        *(f"  - {item}" for item in COMMIT_GROUPING_PLAN),
        "- Suggested commit message drafts (text only):",
        *(f"  - {item}" for item in SUGGESTED_MESSAGES),
        "- Pre-commit verification checklist:",
        *(f"  - {item}" for item in PRE_COMMIT_CHECKLIST),
        "- Rollback note: before committing, discard nothing; use the reviewed diff as the source of truth.",
        "- This plan never stages files or performs Git operations.",
    )
    return "\n".join(lines)
