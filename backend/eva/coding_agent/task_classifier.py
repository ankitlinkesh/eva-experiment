from __future__ import annotations

from .models import CodingClassification


_BLOCKED_PATTERNS = (
    ".env",
    "api key",
    "browser session",
    "cookie",
    "password",
    "secret",
    "token",
    "apply patch",
    "apply this patch",
    "apply this source patch",
    "edit backend",
    "edit source",
    "modify source",
    "change source",
    "write arbitrary",
    "delete file",
    "read c:\\",
    "read /",
    "raw source",
    "source dump",
    "run shell",
    "run powershell",
    "run cmd",
    "terminal command",
    "execute command",
    "run the tests",
    "run tests",
    "execute tests",
    "pytest",
    "pip install",
    "npm install",
    "package install",
    "git ",
    "live llm",
    "call the api",
    "execute tool",
    "quantum code executor",
    "imaginary coding",
    "unknown coding capability",
)


def classify_coding_task(request: str) -> CodingClassification:
    text = " ".join(str(request or "").lower().split())
    if not text:
        return CodingClassification(
            "clarification_needed",
            "codebase_reader_preview",
            False,
            "A coding goal is required before a useful preview can be prepared.",
        )
    if any(pattern in text for pattern in _BLOCKED_PATTERNS):
        return CodingClassification(
            "blocked_execution_request",
            "safety_reviewer_specialist",
            True,
            "The request crosses the Phase 28 preview-only execution or privacy boundary.",
        )
    if any(phrase in text for phrase in ("handoff", "implementation report")):
        return CodingClassification("handoff_report_preview", "handoff_specialist", False, "Handoff preview selected.")
    if any(phrase in text for phrase in ("documentation plan", "docs plan", "document this")):
        return CodingClassification("documentation_plan_preview", "documentation_specialist", False, "Documentation planning selected.")
    if any(phrase in text for phrase in ("safety review", "risk review", "coding risk")):
        return CodingClassification("safety_review_preview", "safety_reviewer_specialist", False, "Safety review selected.")
    if any(phrase in text for phrase in ("test plan", "testing plan", "test checklist")):
        return CodingClassification("test_plan_preview", "test_planning_specialist", False, "Test planning selected.")
    if any(phrase in text for phrase in ("review checklist", "review this", "code review")):
        return CodingClassification("review_checklist_preview", "reviewer_specialist", False, "Review checklist selected.")
    if any(phrase in text for phrase in ("refactor", "cleanup architecture", "restructure")):
        return CodingClassification("refactor_plan_preview", "refactor_planning_specialist", False, "Refactor planning selected.")
    if any(phrase in text for phrase in ("bug", "triage", "regression", "failure")):
        return CodingClassification("bug_triage_preview", "bug_triage_specialist", False, "Bug triage selected.")
    if any(phrase in text for phrase in ("feature", "new capability", "add support")):
        return CodingClassification("feature_plan_preview", "feature_planning_specialist", False, "Feature planning selected.")
    if any(phrase in text for phrase in ("patch plan", "code change", "change plan", "implementation plan")):
        return CodingClassification("patch_plan_preview", "patch_planning_specialist", False, "Patch planning selected.")
    if any(phrase in text for phrase in ("codebase", "understand code", "explain project", "project structure")):
        return CodingClassification("codebase_understanding_preview", "codebase_reader_preview", False, "Codebase-understanding preview selected.")
    return CodingClassification(
        "clarification_needed",
        "codebase_reader_preview",
        False,
        "The request needs a clearer coding goal and remains unexecuted.",
    )
