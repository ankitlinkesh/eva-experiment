from __future__ import annotations

from .models import EvaPlannerStatus


def planner_status() -> EvaPlannerStatus:
    return EvaPlannerStatus(
        planner_version="Planner v3 foundation",
        planning_only=True,
        execution_enabled=False,
        supported_goal_types=[
            "Research Memory retrieval and review",
            "public release/demo/safety previews",
            "explicit v2 dry-run and plan previews",
            "browser/file/message/destructive intent classification",
            "multi-step draft and verification planning",
        ],
        safety_summary=(
            "Planning-only. Does not execute MCP, Playwright, PyAutoGUI, browser control, "
            "screen watching, shell, WhatsApp sending, file writes, vector search, or normal-chat v2 routing."
        ),
    )


def format_planner_status() -> str:
    status = planner_status()
    lines = [
        "Eva Planner v3 status",
        "",
        f"Version: {status.planner_version}",
        "Mode: planning-only",
        f"Execution enabled: {'yes' if status.execution_enabled else 'no'}",
        "",
        "Uses:",
        "- capability registry",
        "- capability permission matrix",
        "- capability-resource mapping",
        "- tool schema previews",
        "- explicit dry-run concepts",
        "",
        "Supported goal types:",
    ]
    lines.extend(f"- {item}" for item in status.supported_goal_types)
    lines.extend(["", "Safety:", status.safety_summary, "", "Scope: explicit planner commands only."])
    return "\n".join(lines)
