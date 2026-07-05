from __future__ import annotations

from .models import EvaSkill, EvaWorkflow
from .registry import get_skill, get_workflow, list_skills, list_workflows
from .selector import select_skills_for_request, select_workflow_for_request
from .workflows import format_fileagent_project_note_workflow


def format_skill_list(items: list[EvaSkill] | None = None) -> str:
    skills = items if items is not None else list_skills()
    lines = ["Eva skills", "", f"Count: {len(skills)}"]
    for item in skills:
        lines.append(f"- {item.id}: {item.name} ({item.category})")
    lines.extend(["", "Scope: skill metadata only. No task was executed."])
    return "\n".join(lines)


def format_skill_detail(skill_id: str) -> str:
    item = get_skill(skill_id)
    if item is None:
        return "\n".join(["Skill detail", "", f"Skill `{skill_id}` was not found.", "Use `eva skills list`."])
    return "\n".join(
        [
            "Skill detail",
            "",
            f"ID: {item.id}",
            f"Name: {item.name}",
            f"Category: {item.category}",
            f"Status: {item.status}",
            "",
            "Description:",
            item.description,
            "",
            "Specialists:",
            *[f"- {specialist_id}" for specialist_id in item.specialists],
            "",
            "Capabilities:",
            *[f"- {capability_id}" for capability_id in item.capabilities],
            "",
            "Safe modes:",
            *[f"- {mode}" for mode in item.safe_modes],
            "",
            "Safety:",
            item.safety_notes,
        ]
    )


def format_skill_selection(request_text: str) -> str:
    selected = select_skills_for_request(request_text)
    lines = ["Skill route", "", f"Request: {request_text}", f"Selected: {', '.join(item.id for item in selected)}"]
    for item in selected[:5]:
        lines.append(f"- {item.name}: {item.description}")
    lines.append("Scope: selection only; no skill executed a task.")
    return "\n".join(lines)


def format_workflow_list(items: list[EvaWorkflow] | None = None) -> str:
    workflows = items if items is not None else list_workflows()
    lines = ["Eva workflows", "", f"Count: {len(workflows)}"]
    for item in workflows:
        lines.append(f"- {item.id}: {item.name} ({item.mode})")
    lines.extend(["", "Scope: workflow metadata only. No task was executed."])
    return "\n".join(lines)


def format_workflow_detail(workflow_id: str) -> str:
    item = get_workflow(workflow_id)
    if item is None:
        return "\n".join(["Workflow detail", "", f"Workflow `{workflow_id}` was not found.", "Use `eva workflows list`."])
    if item.id == "fileagent_project_note_create":
        return format_fileagent_project_note_workflow(item)
    return "\n".join(["Workflow detail", "", f"ID: {item.id}", f"Name: {item.name}", item.description, "No task was executed."])


def format_workflow_selection(request_text: str) -> str:
    workflow = select_workflow_for_request(request_text)
    if workflow is None:
        return "\n".join(["Workflow route", "", f"Request: {request_text}", "Selected: none", "No workflow was executed."])
    return "\n".join(
        [
            "Workflow route",
            "",
            f"Request: {request_text}",
            f"Selected: {workflow.id}",
            f"Mode: {workflow.mode}",
            f"Real scope: {workflow.real_execution_scope}",
            "No workflow step was executed.",
        ]
    )
