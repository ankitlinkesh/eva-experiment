from __future__ import annotations

import re

from .models import ThreatFinding


_INJECTION_MARKERS = ("ignore previous", "ignore all previous", "disregard", "override policy", "bypass safety", "jailbreak")
_IMPERSONATION_MARKERS = ("system:", "developer:", "as developer", "as system", "you are now developer", "you are now system")
_ROLE_MARKERS = ("act as system", "make user rules highest", "user rules highest", "change your role")


def detect_prompt_injection(text: str, source_type: str) -> tuple[ThreatFinding, ...]:
    lowered = str(text or "").lower()
    findings: list[ThreatFinding] = []
    if any(marker in lowered for marker in _INJECTION_MARKERS):
        findings.append(_finding("prompt_injection", "high", source_type, "Prompt-injection markers were found."))
    if any(marker in lowered for marker in _IMPERSONATION_MARKERS):
        findings.append(_finding("system_developer_impersonation", "high", source_type, "System/developer impersonation was detected."))
    if "disregard safety" in lowered or "ignore safety" in lowered or "ignore policy" in lowered:
        findings.append(_finding("policy_ignore", "high", source_type, "Policy-ignore language was detected."))
    if any(marker in lowered for marker in _ROLE_MARKERS):
        findings.append(_finding("role_confusion", "medium", source_type, "Role-confusion language was detected."))
    if re.search(r"[\"'`].*(ignore|disregard|override|tool_call|execute).*?[\"'`]", lowered):
        findings.append(_finding("hidden_instruction", "high", source_type, "Instruction-like text inside quoted or pasted content was treated as untrusted data."))
    return tuple(findings)


def _finding(category: str, severity: str, source_type: str, summary: str) -> ThreatFinding:
    return ThreatFinding(category, severity, source_type, summary, "block_or_treat_as_untrusted_data")
