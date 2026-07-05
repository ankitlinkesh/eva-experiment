from __future__ import annotations

import re

from .models import ThreatFinding


_DIRECT_TOOL_MARKERS = ("tool_call", "call tool", "use tool", "run action", "execute action")
_INDIRECT_TOOL_MARKERS = ("after validation", "quietly trigger", "later trigger", "once approved", "after this check")
_EXECUTION_MARKERS = ("powershell", "terminal", "install a package", "package install", "open browser", "desktop action", "mcp", "cloud action", "shell")
_COMMAND_MARKERS = ("&&", "||", "| sh", "; rm", "rm -rf", "`", "$(")
_KNOWN_CAPABILITIES = {
    "context.status",
    "context.sources",
    "context.policy",
    "context.budget",
    "context.assemble_preview",
    "context.grounding_report",
    "context.redaction_policy",
    "context.readiness",
    "threat.status",
    "threat.catalog",
    "threat.policy",
    "threat.scan_preview",
    "threat.injection_examples",
    "threat.exfiltration_examples",
    "threat.context_guard",
    "threat.readiness",
    "llm.validation_status",
    "llm.red_team_status",
}


def detect_tool_or_capability_requests(text: str, source_type: str) -> tuple[ThreatFinding, ...]:
    raw = str(text or "")
    lowered = raw.lower()
    findings: list[ThreatFinding] = []
    if any(marker in lowered for marker in _DIRECT_TOOL_MARKERS):
        findings.append(_finding("direct_tool_execution", "critical", source_type, "Direct tool/action execution language was detected."))
    if any(marker in lowered for marker in _INDIRECT_TOOL_MARKERS):
        findings.append(_finding("indirect_tool_execution", "critical", source_type, "Indirect or delayed tool execution language was detected."))
    if any(marker in lowered for marker in _EXECUTION_MARKERS):
        findings.append(_finding("execution_surface_request", "critical", source_type, "Locked execution-surface language was detected."))
    if any(marker in lowered for marker in _COMMAND_MARKERS):
        findings.append(_finding("command_injection", "high", source_type, "Command-injection-looking text was detected."))
    if "repair" in lowered and ("executable" in lowered or "action" in lowered or "unsafe" in lowered):
        findings.append(_finding("unsafe_repair", "high", source_type, "Unsafe repair into executable action was requested."))
    for claim in sorted(set(re.findall(r"\b[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\b", raw, flags=re.IGNORECASE))):
        normalized = claim.lower()
        if normalized in _KNOWN_CAPABILITIES:
            continue
        category = "hallucinated_capability" if "superpower" in normalized or "unlocked" in normalized else "unknown_capability"
        severity = "high" if category == "hallucinated_capability" else "medium"
        findings.append(_finding(category, severity, source_type, "Unknown or hallucinated capability claim was flagged."))
    return tuple(findings)


def _finding(category: str, severity: str, source_type: str, summary: str) -> ThreatFinding:
    return ThreatFinding(category, severity, source_type, summary, "block_execution_or_flag_capability")
