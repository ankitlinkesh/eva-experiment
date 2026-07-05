from __future__ import annotations


AUDITED_HEAD = "4f364d2"

DIRTY_TREE_SUMMARY = (
    "The audited baseline was clean on main at 4f364d2 before Phase 30. "
    "The Phase 30 release-candidate patch is intentionally left uncommitted for user review."
)

CHANGED_AREA_GROUPS = (
    "Core routing and command surfaces: RC fast commands and natural-language routes.",
    "Safety metadata: capability registry, resource mappings, and report-only tool schemas.",
    "Planning and review: capability selection, decomposition, and Phase 30 team review.",
    "Status surfaces: Control Center and AI OS release-candidate summaries.",
    "Existing documentation and the master verifier registry.",
)

UNTRACKED_AREA_GROUPS = (
    "Release-candidate package: deterministic models, manifest, plan, hardening, checklist, readiness, status, report, and formatter.",
    "Release-candidate documentation: manifest, commit plan, checklist, hardening report, and candidate overview.",
    "Focused Phase 30 release-candidate verifier.",
)


def dirty_tree_manifest_text() -> str:
    lines = (
        "Eva Phase 30 dirty tree manifest",
        f"- Audited HEAD: {AUDITED_HEAD}.",
        f"- Summary: {DIRTY_TREE_SUMMARY}",
        "- Changed-area groups:",
        *(f"  - {item}" for item in CHANGED_AREA_GROUPS),
        "- Untracked-area groups:",
        *(f"  - {item}" for item in UNTRACKED_AREA_GROUPS),
        "- This is a deterministic audit snapshot; Eva does not run Git or inspect the live filesystem.",
    )
    return "\n".join(lines)
