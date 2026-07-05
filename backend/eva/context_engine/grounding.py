from __future__ import annotations

from .assembler import assemble_context_preview
from .models import ContextPacket, GroundingReport


def build_grounding_report(packet_or_request: ContextPacket | str | None = None) -> GroundingReport:
    packet = packet_or_request if isinstance(packet_or_request, ContextPacket) else assemble_context_preview(str(packet_or_request or "show context grounding report"))
    unsupported = [
        item
        for item in packet.excluded_context
        if "unknown capability" in item.reason.lower()
        or "prompt injection" in item.reason.lower()
        or "stale" in item.reason.lower()
        or "unsupported" in item.reason.lower()
    ]
    stale = tuple(item.reason for item in packet.excluded_context if "stale" in item.reason.lower() or "unknown" in item.reason.lower())
    return GroundingReport(
        packet_id=packet.packet_id,
        supported_sections=len(packet.selected_sections),
        unsupported_assumptions=len(unsupported),
        stale_or_unknown_notes=stale or ("No stale trusted context included.",),
        excluded_count=len(packet.excluded_context),
        readiness=packet.final_readiness,
    )


def grounding_report_text(request: str = "show context grounding report") -> str:
    packet = assemble_context_preview(request)
    report = build_grounding_report(packet)
    lines = [
        "Context Grounding Report",
        "",
        f"Packet ID: {report.packet_id}",
        f"Supported sections: {report.supported_sections}",
        f"Unsupported assumptions marked: {report.unsupported_assumptions}",
        f"Excluded context items: {report.excluded_count}",
        f"Readiness: {report.readiness}",
        "Stale/unknown notes:",
    ]
    lines.extend(f"- {item}" for item in report.stale_or_unknown_notes)
    lines.extend(["", "No live LLM call was made. Context assembly is local/mock preview only. Assembled context cannot execute tools."])
    return "\n".join(lines)
