from __future__ import annotations

from .models import ThreatCategory


_CATEGORIES: tuple[ThreatCategory, ...] = (
    ThreatCategory("prompt_injection", "Prompt injection", "high", "Attempts to override policy or trusted instructions."),
    ThreatCategory("system_developer_impersonation", "System/developer impersonation", "high", "Text pretending to be higher-priority instructions."),
    ThreatCategory("policy_ignore", "Policy-ignore request", "high", "Requests to disregard safety policy or prior instructions."),
    ThreatCategory("role_confusion", "Role confusion", "medium", "Attempts to reorder user, assistant, system, or developer roles."),
    ThreatCategory("hidden_instruction", "Hidden instruction in quoted text", "high", "Instructions embedded in quoted, pasted, webpage-like, or tool-like content."),
    ThreatCategory("context_poisoning", "Context poisoning", "high", "Untrusted context that tries to become instruction."),
    ThreatCategory("malicious_memory", "Malicious memory-like content", "high", "Memory-looking text that asks Eva to ignore policy later."),
    ThreatCategory("malicious_tool_output", "Malicious tool-output-like content", "high", "Tool-looking text that asks Eva to run actions."),
    ThreatCategory("secret_exfiltration", "Secret exfiltration", "critical", "Attempts to reveal secrets, config, tokens, cookies, passwords, or session data."),
    ThreatCategory("browser_session_exfiltration", "Browser-session exfiltration", "critical", "Attempts to access browser session state."),
    ThreatCategory("private_path_exfiltration", "Private-path exfiltration", "high", "Attempts to expose or use private local paths."),
    ThreatCategory("direct_tool_execution", "Direct tool execution request", "critical", "Requests to call a tool or action directly."),
    ThreatCategory("indirect_tool_execution", "Indirect tool execution request", "critical", "Requests to trigger actions after validation or indirectly."),
    ThreatCategory("execution_surface_request", "Browser/desktop/shell/cloud/MCP action request", "critical", "Requests for locked execution surfaces."),
    ThreatCategory("command_injection", "Command-injection-looking text", "high", "Shell-like chaining, piping, or destructive command patterns."),
    ThreatCategory("data_smuggling", "Data smuggling", "medium", "Encoded or hidden text that may carry unsafe instructions."),
    ThreatCategory("unsafe_repair", "Unsafe repair request", "high", "Requests to repair unsafe content into executable actions."),
    ThreatCategory("hallucinated_capability", "Hallucinated capability claim", "high", "Claims a nonexistent privileged capability exists."),
    ThreatCategory("unknown_capability", "Unknown capability claim", "medium", "Mentions unregistered capability identifiers."),
    ThreatCategory("oversized_suspicious_payload", "Oversized suspicious payload", "medium", "Large prompt-like content with suspicious markers."),
    ThreatCategory("nested_suspicious_payload", "Nested suspicious payload", "high", "Nested text or data structures containing unsafe instructions."),
)


def list_threat_categories() -> tuple[ThreatCategory, ...]:
    return _CATEGORIES


def threat_catalog_text() -> str:
    lines = ["Threat Catalog", ""]
    for item in _CATEGORIES:
        lines.append(f"- {item.id}: {item.name} ({item.severity}) - {item.description}")
    lines.extend(
        [
            "",
            "No live LLM call was made.",
            "Threat defense is local/mock preview only.",
            "Untrusted context cannot override system/developer/safety policy.",
            "Secrets/config/session data are blocked.",
            "Defended context cannot execute tools.",
        ]
    )
    return "\n".join(lines)
