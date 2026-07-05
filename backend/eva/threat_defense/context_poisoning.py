from __future__ import annotations

from .models import ThreatFinding


_POISON_MARKERS = ("context says", "retrieved context says", "webpage says", "tool output:", "memory:", "remember this:", "next time")
_DATA_SMUGGLING_MARKERS = ("base64:", "encoded:", "decode this", "hidden payload")


def detect_context_poisoning(text: str, source_type: str) -> tuple[ThreatFinding, ...]:
    lowered = str(text or "").lower()
    findings: list[ThreatFinding] = []
    if any(marker in lowered for marker in _POISON_MARKERS) and any(marker in lowered for marker in ("ignore", "override", "execute", "trigger", "policy")):
        findings.append(_finding("context_poisoning", "high", source_type, "Untrusted context attempted to become instruction."))
    if "memory:" in lowered or "remember this:" in lowered or "next time" in lowered:
        findings.append(_finding("malicious_memory", "high", source_type, "Memory-like text attempted to carry unsafe instructions."))
    if "tool output:" in lowered or "tool result:" in lowered:
        findings.append(_finding("malicious_tool_output", "high", source_type, "Tool-output-like text attempted to request action."))
    if any(marker in lowered for marker in _DATA_SMUGGLING_MARKERS):
        findings.append(_finding("data_smuggling", "medium", source_type, "Encoded or hidden instruction-like content was detected."))
    if (lowered.count("{") + lowered.count("[") >= 2) and any(marker in lowered for marker in ("ignore", "override", "instruction", "tool_call")):
        findings.append(_finding("nested_suspicious_payload", "high", source_type, "Nested suspicious payload was detected."))
    if len(str(text or "")) > 6_000 and any(marker in lowered for marker in ("ignore", "secret", "tool", "execute", "policy")):
        findings.append(_finding("oversized_suspicious_payload", "medium", source_type, "Oversized suspicious payload was trimmed or blocked."))
    return tuple(findings)


def _finding(category: str, severity: str, source_type: str, summary: str) -> ThreatFinding:
    return ThreatFinding(category, severity, source_type, summary, "treat_as_untrusted_data")
