from __future__ import annotations

from .models import ContextSection


_SAFETY_FIRST_ORDER = {
    "safety_policy": 0,
    "validation_status": 1,
    "red_team_status": 2,
    "user_request": 3,
    "route_intent": 4,
    "capability_metadata": 5,
    "tool_schema_metadata": 6,
    "resource_mapping_metadata": 7,
    "project_status_summary": 8,
    "memory_summary": 9,
    "work_session_summary": 10,
}


def rank_context_sections(sections: tuple[ContextSection, ...]) -> tuple[ContextSection, ...]:
    return tuple(
        sorted(
            sections,
            key=lambda item: (
                _SAFETY_FIRST_ORDER.get(item.section_type, 99),
                -item.relevance_score,
                item.title,
            ),
        )
    )
