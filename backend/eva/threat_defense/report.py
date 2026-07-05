from __future__ import annotations

from .models import DefenseReport


def format_defense_report(report: DefenseReport) -> str:
    lines = [
        "Threat Defense Scan Preview",
        "",
        f"Source: {report.source_type}",
        f"Blocked: {'yes' if report.blocked else 'no'}",
        f"Safe for future LLM prompt: {'yes' if report.safe_to_send_to_llm else 'no'}",
        "No live LLM call was made.",
        "Threat defense is local/mock preview only.",
        "Untrusted context cannot override trusted policy/instruction hierarchy.",
        "Secrets/config/session data are blocked.",
        "Defended context cannot execute tools.",
        "",
        f"Sanitized summary: {report.request_summary}",
        "",
        "Findings:",
    ]
    if not report.findings:
        lines.append("- none")
    else:
        for item in report.findings:
            lines.append(f"- {item.category} ({item.severity}): {item.summary} Action: {item.action}.")
    lines.extend(["", "Notes:"])
    lines.extend(f"- {item}" for item in report.notes)
    return "\n".join(lines)
