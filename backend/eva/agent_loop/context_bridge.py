from __future__ import annotations

from ..context_engine.assembler import assemble_context_preview


def build_context_summary(request: str) -> tuple[object, str]:
    packet = assemble_context_preview(request)
    summary = f"{packet.packet_id}; sections={len(packet.selected_sections)}; excluded={len(packet.excluded_context)}"
    return packet, summary
