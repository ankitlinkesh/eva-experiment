from __future__ import annotations


def grounding_notes_for(source_type: str, trust_level: str, text: str) -> tuple[str, ...]:
    lowered = str(text or "").lower()
    notes = ["Grounding checked against local policy metadata only."]
    if source_type in {"project_checkpoint", "verification_evidence"}:
        notes.append("Project memory should be grounded in verifier/status evidence when used.")
    if trust_level == "unknown_or_stale":
        notes.append("Unknown or stale memory is not trusted without current evidence.")
    if "imaginary" in lowered or "super capability" in lowered:
        notes.append("Hallucinated capability claim is not grounded and is excluded.")
    return tuple(notes)
