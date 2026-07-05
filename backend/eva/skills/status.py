from __future__ import annotations

from .registry import list_skills, list_workflows, validate_unique_skill_ids, validate_unique_workflow_ids


def format_skill_status() -> str:
    skills = list_skills()
    categories = sorted({item.category for item in skills})
    return "\n".join(
        [
            "Skills status",
            "",
            f"Registered skills: {len(skills)}",
            f"Unique IDs: {'yes' if validate_unique_skill_ids() else 'no'}",
            f"Categories: {', '.join(categories)}",
            "Execution: metadata, route selection, draft/workflow planning only.",
            "Safety: no broad file writes, MCP, browser control, desktop control, terminal execution, package installs, or cloud calls.",
        ]
    )


def format_workflow_status() -> str:
    workflows = list_workflows()
    return "\n".join(
        [
            "Workflows status",
            "",
            f"Registered workflows: {len(workflows)}",
            f"Unique IDs: {'yes' if validate_unique_workflow_ids() else 'no'}",
            "Main workflow: fileagent_project_note_create",
            "Real scope: Phase 12L create-new-text-file only, after approval and exact confirmation.",
            "Execution: workflow plans only from this layer.",
        ]
    )
