from __future__ import annotations

from .assembler import assemble_context_preview
from .models import ContextPacket


def format_context_packet(packet: ContextPacket) -> str:
    lines = [
        "Context Assembly Preview",
        "",
        f"Packet ID: {packet.packet_id}",
        f"User request summary: {packet.user_request_summary}",
        f"Readiness: {packet.final_readiness}",
        "No live LLM call was made.",
        "Context assembly is local/mock preview only.",
        "Assembled context cannot execute tools.",
        "",
        "Selected context sections:",
    ]
    for section in packet.selected_sections:
        lines.extend(
            [
                f"- {section.title}",
                f"  Type: {section.section_type}",
                f"  Source: {section.source_type} / {section.source_name}",
                f"  Trust: {section.source_trust_level}",
                f"  Relevance: {section.relevance_score:.2f}",
                f"  Budget estimate: {section.budget_estimate_chars} chars",
                f"  Redaction: {section.redaction_status}",
                f"  Trimmed: {'yes' if section.trimmed else 'no'}",
                f"  Safety: {'; '.join(section.safety_notes)}",
                f"  Grounding: {'; '.join(section.grounding_notes)}",
                f"  Content: {section.content}",
            ]
        )
    lines.extend(["", "Excluded context:"])
    lines.extend(f"- {item.source_type}: {item.name} - {item.reason}" for item in packet.excluded_context)
    lines.extend(["", "Grounding notes:"])
    lines.extend(f"- {item}" for item in packet.grounding_notes)
    lines.extend(["", "Safety notes:"])
    lines.extend(f"- {item}" for item in packet.safety_notes)
    return "\n".join(lines)


def build_context_report(request: str = "show context assembly status") -> str:
    return format_context_packet(assemble_context_preview(request))
