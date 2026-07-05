from __future__ import annotations

from ..threat_defense.guard import scan_threat_preview


def build_threat_summary(content: object, *, source_type: str = "agent_loop_request") -> tuple[object, str, bool]:
    report = scan_threat_preview(content, source_type=source_type)
    categories = ", ".join(item.category for item in report.findings) if report.findings else "none"
    summary = f"blocked={report.blocked}; findings={categories}"
    return report, summary, report.blocked
