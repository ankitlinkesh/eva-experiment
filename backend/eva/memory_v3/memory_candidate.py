from __future__ import annotations

import hashlib

from .conflict_detection import detect_conflict
from .freshness import classify_freshness
from .grounding import grounding_notes_for
from .injection_guard import detect_injection
from .models import MemoryV3Record
from .privacy_filter import classify_privacy, redact_memory_text
from .source_model import classify_source
from .trust_scoring import trust_for_source


def build_memory_candidate(text: str, *, created_at: str = "metadata unavailable", updated_at: str = "metadata unavailable") -> MemoryV3Record:
    source_type = classify_source(text)
    privacy_class, flags, privacy_reason = classify_privacy(text)
    injection, injection_reason = detect_injection(text)
    if injection:
        source_type = "untrusted_text"
        privacy_class = "blocked"
        flags = tuple(dict.fromkeys(flags + ("prompt_injection_like",)))
        privacy_reason = injection_reason
    trust_level, confidence = trust_for_source(source_type, text)
    if injection:
        trust_level, confidence = "untrusted_injected_text", 0.0
    freshness = classify_freshness(text)
    conflict_status, conflict_reason = detect_conflict(text)
    summary = _safe_summary(text)
    grounding = grounding_notes_for(source_type, trust_level, text)
    exclusion_reason = _exclusion_reason(
        privacy_class=privacy_class,
        trust_level=trust_level,
        freshness=freshness,
        conflict_status=conflict_status,
        privacy_reason=privacy_reason,
        injection_reason=injection_reason,
        conflict_reason=conflict_reason,
        text=text,
    )
    eligibility = "excluded" if exclusion_reason else "eligible"
    readiness = "ready_for_context_preview" if eligibility == "eligible" else "blocked_or_marked"
    return MemoryV3Record(
        memory_id=_memory_id(text),
        memory_summary=summary,
        source_type=source_type,
        source_trust_level=trust_level,
        created_at=created_at,
        updated_at=updated_at,
        freshness_status=freshness,
        confidence_score=round(confidence, 2),
        privacy_class=privacy_class,
        sensitivity_flags=flags,
        conflict_status=conflict_status,
        grounding_notes=grounding,
        context_injection_eligibility=eligibility,
        exclusion_reason=exclusion_reason,
        final_readiness_status=readiness,
        local_only_statement="Memory v3 is local only.",
        no_live_llm_call_statement="No live LLM call was made.",
        no_cloud_memory_statement="No cloud memory is used.",
    )


def _memory_id(text: str) -> str:
    return "memv3_" + hashlib.sha256(("phase21|" + str(text or "")).encode("utf-8")).hexdigest()[:12]


def _safe_summary(text: str) -> str:
    clean = redact_memory_text(text)
    if not clean:
        return "Empty memory candidate."
    if len(clean) <= 180:
        return clean
    return clean[:160].rstrip() + " ... [trimmed]"


def _exclusion_reason(
    *,
    privacy_class: str,
    trust_level: str,
    freshness: str,
    conflict_status: str,
    privacy_reason: str,
    injection_reason: str,
    conflict_reason: str,
    text: str,
) -> str:
    lowered = str(text or "").lower()
    if privacy_class.startswith("sensitive") or privacy_class == "blocked":
        return privacy_reason or "Sensitive memory is excluded."
    if injection_reason:
        return injection_reason
    if "imaginary" in lowered or "super capability" in lowered:
        return "Unknown or hallucinated capability memory is not trusted."
    if freshness == "stale":
        return "Stale memory is marked stale and excluded from context injection."
    if conflict_status != "no_conflict_detected":
        return conflict_reason
    if trust_level in {"untrusted_external_text", "untrusted_injected_text", "unknown_or_stale"}:
        return "Unknown or untrusted memory is excluded until grounded."
    return ""
