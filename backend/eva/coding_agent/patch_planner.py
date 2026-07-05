from __future__ import annotations


def build_patch_plan(task_type: str) -> tuple[tuple[str, ...], str]:
    focus = {
        "codebase_understanding_preview": "Map the relevant metadata surfaces and clarify the requested subsystem.",
        "bug_triage_preview": "Define the symptom, expected behavior, reproduction evidence, and likely ownership boundary.",
        "feature_plan_preview": "Define acceptance criteria, affected interfaces, safety constraints, and verification evidence.",
        "refactor_plan_preview": "Define preserved behavior, migration boundaries, compatibility risks, and regression evidence.",
        "patch_plan_preview": "Describe the smallest file-level change sequence and its expected verification.",
        "review_checklist_preview": "Review scope, correctness, compatibility, safety, tests, and documentation.",
        "test_plan_preview": "List deterministic checks, negative cases, integration checks, and completion evidence.",
        "safety_review_preview": "Identify authority, privacy, execution, and write-path risks before implementation.",
        "documentation_plan_preview": "List the minimal status, capability, threat-model, and verification documentation changes.",
        "handoff_report_preview": "Summarize scope, decisions, evidence, remaining limits, and next safe step.",
        "clarification_needed": "Ask for the coding outcome, affected subsystem, and success criteria.",
    }.get(task_type, "Refuse the execution request and explain the preview-only boundary.")
    steps = (
        focus,
        "Confirm the change stays within existing Eva architecture and safety gates.",
        "Prepare a human-reviewed file-by-file plan without source modification.",
        "Recommend focused and regression verification for a developer to run manually.",
        "Record limitations and the next safe handoff step.",
    )
    return steps, "Planning text only; no diff was generated and no patch was applied."
