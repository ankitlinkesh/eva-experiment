from __future__ import annotations

from .registry import list_specialists, validate_unique_specialist_ids


def format_specialist_status() -> str:
    specialists = list_specialists()
    categories = sorted({item.category for item in specialists})
    return "\n".join(
        [
            "Specialists status",
            "",
            f"Registered specialists: {len(specialists)}",
            f"Unique IDs: {'yes' if validate_unique_specialist_ids() else 'no'}",
            f"Categories: {', '.join(categories)}",
            "Execution: selection and workflow guidance only.",
            "Safety: no MCP, browser control, desktop control, terminal execution, cloud calls, or broad file writes are enabled.",
        ]
    )
