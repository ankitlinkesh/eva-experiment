from __future__ import annotations

from .budget import budget_policy_text
from .context_policy import context_policy_text
from .grounding import grounding_report_text
from .redaction import redaction_policy_text
from .report import build_context_report
from .source_registry import format_source_registry
from .status import get_context_engine_status


def _boundary() -> str:
    return "\n".join(
        [
            "No live LLM call was made.",
            "Context assembly is local/mock preview only.",
            "Secrets/config/session data are blocked.",
            "Invalid or injected context cannot become trusted instruction.",
            "Assembled context cannot execute tools.",
            "No provider SDKs, arbitrary file reads, browser/desktop/shell/cloud/MCP execution, or new write paths are enabled.",
        ]
    )


def format_context_status() -> str:
    status = get_context_engine_status()
    return "\n".join(
        [
            "Context Assembly Engine Status",
            "",
            f"Status: {status.status}.",
            f"Mode: {status.mode}.",
            f"Live LLM calls enabled: {'yes' if status.live_llm_calls_enabled else 'no'}.",
            f"Provider SDKs enabled: {'yes' if status.provider_sdks_enabled else 'no'}.",
            f"Tool execution enabled: {'yes' if status.tool_execution_enabled else 'no'}.",
            f"Arbitrary file reads enabled: {'yes' if status.arbitrary_file_reads_enabled else 'no'}.",
            f"Secret/config/session reads enabled: {'yes' if status.secret_config_session_reads_enabled else 'no'}.",
            f"Next phase: {status.next_phase}.",
            "",
            _boundary(),
        ]
    )


def format_context_sources() -> str:
    return format_source_registry()


def format_context_policy() -> str:
    return context_policy_text()


def format_context_budget() -> str:
    return budget_policy_text()


def format_context_assemble_preview(request: str = "show context assembly status") -> str:
    return build_context_report(request)


def format_context_grounding_report(request: str = "show context grounding report") -> str:
    return grounding_report_text(request)


def format_context_redaction_policy() -> str:
    return redaction_policy_text()


def format_context_readiness() -> str:
    return "\n".join(
        [
            "Context Assembly Readiness",
            "",
            "Ready now: deterministic local source registry, policy, budget, redaction, ranking, assembly preview, grounding report, commands, ask routes, Control Center, capabilities, planner, and team-review status.",
            "Not ready now: live LLM/API/provider calls, provider SDKs, secret/config/session reads, arbitrary file reads, tool execution, browser execution, desktop execution, shell/package/cloud/MCP execution, or new write paths.",
            "Next phase: Phase 17 LLM Threat Defense + Prompt Injection Guard.",
            "",
            _boundary(),
        ]
    )
