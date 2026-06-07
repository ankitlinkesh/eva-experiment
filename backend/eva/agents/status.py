from __future__ import annotations

from dataclasses import asdict

from ..schemas.modeling import schema_dataclass


@schema_dataclass
class AgentFrameworkStatus:
    version: str
    lifecycle_available: bool
    dry_run_delegation_available: bool
    execution_enabled: bool
    safety_summary: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

    model_dump = as_dict


def agent_framework_status() -> AgentFrameworkStatus:
    return AgentFrameworkStatus(
        version="Agent Framework v1",
        lifecycle_available=True,
        dry_run_delegation_available=True,
        execution_enabled=False,
        safety_summary=(
            "Execution disabled except existing explicit safe read-only delegates. "
            "No MCP, Playwright, PyAutoGUI, browser control, screen watching, shell, file writes, "
            "WhatsApp sending, or normal-chat routing through Agent Framework is enabled."
        ),
    )


def format_agent_framework_status() -> str:
    status = agent_framework_status()
    return "\n".join(
        [
            "Agent Framework v1 status",
            "",
            f"Lifecycle interface: {'available' if status.lifecycle_available else 'unavailable'}",
            f"Dry-run delegation: {'available' if status.dry_run_delegation_available else 'unavailable'}",
            f"Execution enabled: {'yes' if status.execution_enabled else 'no'}",
            "",
            "Lifecycle:",
            "- plan",
            "- dry_run",
            "- execute",
            "- observe",
            "- verify",
            "- rollback",
            "- explain",
            "",
            "Safety:",
            status.safety_summary,
            "",
            "Scope: explicit agent framework commands only. No normal chat routing was changed.",
        ]
    )

