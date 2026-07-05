from __future__ import annotations

import re
from typing import Any

from .context_poisoning import detect_context_poisoning
from .exfiltration_detector import detect_exfiltration
from .injection_detector import detect_prompt_injection
from .models import DefenseReport, ThreatFinding
from .tool_request_detector import detect_tool_or_capability_requests


_PRIVATE_PATH = re.compile(r"\b[A-Za-z]:\\Users\\[^ \n\r\t,;]+", re.IGNORECASE)
_SECRET_ASSIGNMENT = re.compile(r"\b[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|COOKIE|PASSWORD|SESSION)\s*[:=]\s*[^\s,;]+", re.IGNORECASE)


def scan_threat_preview(content: object, *, source_type: str = "user_request") -> DefenseReport:
    text = _extract_text(content)
    sanitized = _sanitize(text)
    findings = _dedupe_findings(
        detect_prompt_injection(text, source_type)
        + detect_exfiltration(text, source_type)
        + detect_tool_or_capability_requests(text, source_type)
        + detect_context_poisoning(text, source_type)
    )
    blocked = bool(findings)
    return DefenseReport(
        request_summary=_summarize(sanitized),
        source_type=source_type,
        findings=findings,
        blocked=blocked,
        safe_to_send_to_llm=not blocked,
        no_llm_call_made=True,
        tool_execution_enabled=False,
        notes=(
            "No live LLM call was made.",
            "Threat defense is local/mock preview only.",
            "Untrusted context cannot override trusted policy/instruction hierarchy.",
            "Secrets/config/session data are blocked.",
            "Defended context cannot execute tools.",
        ),
    )


def _extract_text(content: object) -> str:
    if hasattr(content, "selected_sections") and hasattr(content, "grounding_notes"):
        sections = getattr(content, "selected_sections", ()) or ()
        excluded = getattr(content, "excluded_context", ()) or ()
        bits: list[str] = []
        for section in sections:
            bits.append(str(getattr(section, "content", "")))
            bits.extend(str(item) for item in getattr(section, "safety_notes", ()) or ())
        for item in excluded:
            bits.append(str(getattr(item, "reason", "")))
        bits.extend(str(item) for item in getattr(content, "grounding_notes", ()) or ())
        return "\n".join(bits)
    return str(content or "")


def _sanitize(text: str) -> str:
    clean = _SECRET_ASSIGNMENT.sub("[redacted secret-like value]", str(text or ""))
    clean = _PRIVATE_PATH.sub("[redacted private path]", clean)
    clean = re.sub(r"\.env(?:\.local)?", "[blocked config file]", clean, flags=re.IGNORECASE)
    clean = clean.replace("{'", "{ [quoted key] ").replace("'}", "[quoted value] }")
    return clean


def _summarize(text: str) -> str:
    clean = " ".join(str(text or "").split())
    if len(clean) <= 360:
        return clean or "No request text supplied."
    return clean[:320].rstrip() + " ... [trimmed]"


def _dedupe_findings(findings: tuple[ThreatFinding, ...]) -> tuple[ThreatFinding, ...]:
    seen: set[tuple[str, str]] = set()
    kept: list[ThreatFinding] = []
    for item in findings:
        key = (item.category, item.source_type)
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return tuple(kept)
