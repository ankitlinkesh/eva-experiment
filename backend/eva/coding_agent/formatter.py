from __future__ import annotations

from .coding_policy import (
    BOUNDARY_LINES,
    blocked_actions_text,
    coding_policy_text,
    coding_specialists_text,
)
from .project_context import build_project_context_summary
from .report import build_coding_report
from .status import get_coding_status


def _format_output(title: str, body: str) -> str:
    return "\n".join((title, body, "", *BOUNDARY_LINES))


def _bullets(items: tuple[str, ...]) -> str:
    return "\n".join(f"- {item}" for item in items)


def format_coding_status() -> str:
    status = get_coding_status()
    body = "\n".join(
        (
            f"Mode: {status.mode}.",
            f"Source editing enabled: {status.source_editing_enabled}.",
            f"Patch application enabled: {status.patch_application_enabled}.",
            f"Execution enabled: {status.execution_enabled}.",
            f"Readiness: {status.readiness}.",
            f"Next phase: {status.next_phase}.",
        )
    )
    return _format_output("Coding Specialist / CodingAgent status", body)


def format_coding_policy() -> str:
    return _format_output("Coding Specialist / CodingAgent policy", coding_policy_text())


def format_coding_specialists() -> str:
    return _format_output("Coding Specialist catalog", coding_specialists_text())


def format_coding_task_preview(request: str = "plan a code change") -> str:
    report = build_coding_report(request)
    body = "\n".join(
        (
            f"Report ID: {report.coding_report_id}.",
            f"Task type: {report.coding_task_type}.",
            f"Specialist mode: {report.selected_specialist_mode}.",
            f"Request summary: {report.user_request_summary}",
            f"Readiness: {report.final_readiness_status}.",
        )
    )
    return _format_output("Coding task preview", body)


def format_coding_project_context() -> str:
    context = build_project_context_summary()
    body = "\n".join(
        (
            context.summary,
            f"Policy: {context.policy}",
            "Safe context sources:",
            _bullets(context.sources),
        )
    )
    return _format_output("Coding project-context preview", body)


def format_coding_patch_plan(request: str = "plan a code change") -> str:
    report = build_coding_report(request)
    body = "\n".join(
        (
            f"Task type: {report.coding_task_type}.",
            "Proposed plan:",
            _bullets(report.proposed_plan),
            f"Patch preview: {report.patch_preview_summary}",
        )
    )
    return _format_output("Coding patch-plan preview", body)


def format_coding_review_checklist(request: str = "review this coding task") -> str:
    report = build_coding_report(request)
    return _format_output("Coding review-checklist preview", _bullets(report.review_checklist))


def format_coding_test_plan(request: str = "show coding test plan") -> str:
    report = build_coding_report(request)
    return _format_output("Coding test-plan preview", _bullets(report.test_plan_preview))


def format_coding_risk_review(request: str = "show coding risk review") -> str:
    report = build_coding_report(request)
    body = "\n".join(
        (
            "Risk review:",
            _bullets(report.risk_review),
            "Blocked actions:",
            _bullets(report.blocked_actions_with_reasons),
        )
    )
    return _format_output("Coding safety/risk review preview", body)


def format_coding_handoff(request: str = "prepare a coding handoff report") -> str:
    report = build_coding_report(request)
    body = "\n".join(
        (
            f"Task type: {report.coding_task_type}.",
            f"Specialist mode: {report.selected_specialist_mode}.",
            "Handoff notes:",
            _bullets(report.handoff_notes),
            "Verification recommendations:",
            _bullets(report.verification_recommendations),
        )
    )
    return _format_output("Coding handoff-report preview", body)


def format_coding_blocked_actions() -> str:
    return _format_output("CodingAgent blocked-action report", blocked_actions_text())


def format_coding_readiness() -> str:
    status = get_coding_status()
    body = "\n".join(
        (
            f"Readiness: {status.readiness}.",
            "Available: deterministic classification, plans, reviews, test instructions, risk review, and handoff reports.",
            "Locked: source editing, patch application, and every execution surface.",
            f"Next phase: {status.next_phase}.",
        )
    )
    return _format_output("Coding Specialist readiness", body)
