from __future__ import annotations

from .models import SpecialistRole
from .registry import get_specialist, list_specialists
from .selector import select_specialists_for_request


def format_specialist_list(items: list[SpecialistRole] | None = None) -> str:
    specialists = items if items is not None else list_specialists()
    lines = ["Eva specialists", "", f"Count: {len(specialists)}"]
    for item in specialists:
        lines.append(f"- {item.id}: {item.name} ({item.category})")
    lines.extend(["", "Scope: role selection only. No task was executed."])
    return "\n".join(lines)


def format_specialist_detail(specialist_id: str) -> str:
    item = get_specialist(specialist_id)
    if item is None:
        return "\n".join(["Specialist detail", "", f"Specialist `{specialist_id}` was not found.", "Use `eva specialists list`."])
    return "\n".join(
        [
            "Specialist detail",
            "",
            f"ID: {item.id}",
            f"Name: {item.name}",
            f"Category: {item.category}",
            "",
            "Description:",
            item.description,
            "",
            "Primary capabilities:",
            *[f"- {capability_id}" for capability_id in item.primary_capabilities],
            "",
            "Safe modes:",
            *[f"- {mode}" for mode in item.safe_modes],
            "",
            "Unavailable actions:",
            *[f"- {action}" for action in item.unavailable_actions],
            "",
            "Safety:",
            item.safety_notes,
        ]
    )


def format_specialist_selection(request_text: str) -> str:
    selected = select_specialists_for_request(request_text)
    lines = ["Specialist route", "", f"Request: {request_text}", f"Selected: {', '.join(item.id for item in selected)}"]
    for item in selected[:5]:
        lines.append(f"- {item.name}: {item.description}")
    lines.append("Scope: selection only; no specialist executed a task.")
    return "\n".join(lines)
