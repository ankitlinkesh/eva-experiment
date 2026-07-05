from __future__ import annotations

from .memory_policy import boundary_lines
from .models import MemoryRetrievalPreview, MemoryV3Record


def format_memory_record(record: MemoryV3Record) -> str:
    lines = [
        "Memory v3 record preview",
        *boundary_lines(),
        "Record:",
        f"- Memory ID: {record.memory_id}",
        f"- Memory summary: {record.memory_summary}",
        f"- Source type: {record.source_type}",
        f"- Source trust level: {record.source_trust_level}",
        f"- Created timestamp metadata: {record.created_at}",
        f"- Updated timestamp metadata: {record.updated_at}",
        f"- Freshness status: {record.freshness_status}",
        f"- Confidence score: {record.confidence_score}",
        f"- Privacy class: {record.privacy_class}",
        f"- Sensitivity flags: {', '.join(record.sensitivity_flags) if record.sensitivity_flags else 'none'}",
        f"- Conflict status: {record.conflict_status}",
        f"- Context injection eligibility: {record.context_injection_eligibility}",
        f"- Exclusion reason: {record.exclusion_reason or 'none'}",
        f"- Final readiness status: {record.final_readiness_status}",
        "Grounding notes:",
    ]
    lines.extend(f"- {item}" for item in record.grounding_notes)
    return "\n".join(lines)


def format_retrieval_preview(preview: MemoryRetrievalPreview) -> str:
    lines = [
        "Memory v3 retrieval preview",
        *boundary_lines(),
        f"Preview ID: {preview.preview_id}",
        f"Request summary: {preview.request_summary}",
        f"Final readiness status: {preview.final_readiness_status}",
        "Included memory summaries:",
    ]
    if preview.included_records:
        lines.extend(f"- {item.memory_id}: {item.memory_summary}; reason: eligible safe grounded summary" for item in preview.included_records)
    else:
        lines.append("- none")
    lines.append("Excluded memory summaries:")
    if preview.excluded_records:
        lines.extend(f"- {item.memory_id}: {item.exclusion_reason or 'not eligible'}" for item in preview.excluded_records)
    else:
        lines.append("- none")
    lines.append("Context rules:")
    lines.extend(f"- {item}" for item in preview.context_rules)
    lines.append("Safety notes:")
    lines.extend(f"- {item}" for item in preview.safety_notes)
    return "\n".join(lines)
