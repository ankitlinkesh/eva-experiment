from __future__ import annotations


def trust_for_source(source_type: str, text: str = "") -> tuple[str, float]:
    lowered = str(text or "").lower()
    if "ignore policy" in lowered or "execute tool" in lowered:
        return "untrusted_injected_text", 0.0
    if "imaginary" in lowered or "super capability" in lowered or "hallucinated" in lowered:
        return "unknown_or_stale", 0.1
    if source_type in {"user_explicit_memory", "user_preference"}:
        return "trusted_explicit_user", 0.9
    if source_type in {"project_checkpoint", "verification_evidence"}:
        return "trusted_verified_project_evidence", 0.88
    if source_type in {"workflow_state_summary", "work_session_summary", "fileagent_summary", "system_status_summary"}:
        return "trusted_local_status", 0.82
    if source_type in {"research_memory_summary", "generated_summary"}:
        return "semi_trusted_summary", 0.62
    if source_type == "untrusted_text":
        return "untrusted_external_text", 0.2
    return "unknown_or_stale", 0.25
