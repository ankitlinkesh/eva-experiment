from __future__ import annotations

from copy import deepcopy
from typing import Any

from .permissions import format_permission_summary_line, get_capability_permission


_SCHEMA_ALIASES = {
    "research_memory.save": "research_memory.import_note",
    "research_memory.export": "research_memory.export_json",
    "eva_v2.plan": "eva_v2.plan_preview",
    "public_release.demo": "public_release.demo_scenarios",
    "public_release.safety_test": "public_release.safety_simulator",
    "public_release.doctor": "public_release.ready_check",
}


_SCHEMAS: dict[str, dict[str, Any]] = {
    "research_memory.status": {
        "name": "Research Memory Status",
        "description": "Show local Research Memory status without paths.",
        "parameters": [],
        "execution_status": "read_only_metadata",
    },
    "research_memory.help": {
        "name": "Research Memory Help",
        "description": "Show the local Research Memory command guide.",
        "parameters": [],
        "execution_status": "read_only_metadata",
    },
    "research_memory.search": {
        "name": "Research Memory Search",
        "description": "Lexically search sanitized local research notes.",
        "parameters": [
            {"name": "query", "type": "string", "required": True},
            {"name": "topic", "type": "string", "required": False},
            {"name": "tag", "type": "string", "required": False},
        ],
        "execution_status": "read_only_local",
    },
    "research_memory.retrieve": {
        "name": "Research Memory Retrieve",
        "description": "Retrieve ranked local research snippets for explicit v2 context.",
        "parameters": [
            {"name": "query", "type": "string", "required": True},
            {"name": "limit", "type": "integer", "required": False},
            {"name": "topic", "type": "string", "required": False},
            {"name": "tag", "type": "string", "required": False},
        ],
        "execution_status": "read_only_local",
    },
    "research_memory.topic_summary": {
        "name": "Research Memory Topic Summary",
        "description": "Summarize one saved topic from sanitized local notes.",
        "parameters": [{"name": "topic", "type": "string", "required": True}],
        "execution_status": "read_only_local",
    },
    "research_memory.import_note": {
        "name": "Research Memory Save Note",
        "description": "Save a user-provided local note after redaction and quality metadata checks.",
        "parameters": [
            {"name": "topic", "type": "string", "required": True},
            {"name": "title", "type": "string", "required": False},
            {"name": "text", "type": "string", "required": True},
            {"name": "tags", "type": "string_list", "required": False},
        ],
        "execution_status": "explicit_local_write",
    },
    "research_memory.export_json": {
        "name": "Research Memory Export JSON",
        "description": "Export sanitized local notes to ignored runtime storage and return a filename only.",
        "parameters": [{"name": "topic", "type": "string", "required": False}],
        "execution_status": "explicit_local_write",
    },
    "research_memory.stats": {
        "name": "Research Memory Stats",
        "description": "Show path-free local storage statistics.",
        "parameters": [],
        "execution_status": "read_only_metadata",
    },
    "research_memory.tags": {
        "name": "Research Memory Tags",
        "description": "List normalized tags with item counts.",
        "parameters": [],
        "execution_status": "read_only_local",
    },
    "research_memory.quality": {
        "name": "Research Memory Quality",
        "description": "Preview short, duplicate-like, or low-value notes without deleting them.",
        "parameters": [],
        "execution_status": "read_only_local",
    },
    "research_memory.duplicates_preview": {
        "name": "Research Memory Duplicates Preview",
        "description": "Preview exact and near-duplicate groups without merging or deleting.",
        "parameters": [],
        "execution_status": "read_only_local",
    },
    "research_memory.ranking_status": {
        "name": "Research Memory Ranking Status",
        "description": "Explain lexical-first ranking, recency, quality, penalties, and diversity reranking.",
        "parameters": [],
        "execution_status": "read_only_metadata",
    },
    "research_memory.recall_stats": {
        "name": "Research Memory Recall Stats",
        "description": "Show local recall counts without exposing raw query strings.",
        "parameters": [{"name": "limit", "type": "integer", "required": False}],
        "execution_status": "read_only_local",
    },
    "research_memory.promote_candidates": {
        "name": "Research Memory Promotion Candidates",
        "description": "Preview useful long-term notes without auto-promotion or writes.",
        "parameters": [{"name": "limit", "type": "integer", "required": False}],
        "execution_status": "read_only_local",
    },
    "research_memory.review_memory": {
        "name": "Research Memory Review",
        "description": "Show local memory quality, recall, duplicate, and safe next-command review.",
        "parameters": [],
        "execution_status": "read_only_local",
    },
    "eva_v2.plan_preview": {
        "name": "Eva v2 Plan Preview",
        "description": "Preview a typed v2 plan for an explicit request without risky execution.",
        "parameters": [{"name": "request", "type": "string", "required": True}],
        "execution_status": "dry_run_only",
    },
    "eva_v2.route_preview": {
        "name": "Eva v2 Route Preview",
        "description": "Preview v2 route selection without routing normal chat through v2.",
        "parameters": [{"name": "request", "type": "string", "required": True}],
        "execution_status": "dry_run_only",
    },
    "eva_v2.dry_run": {
        "name": "Eva v2 Dry Run",
        "description": "Run explicit v2 planning and safe bridge preview without risky execution.",
        "parameters": [{"name": "request", "type": "string", "required": True}],
        "execution_status": "dry_run_only",
    },
    "public_release.demo_scenarios": {
        "name": "Public Release Demo Scenarios",
        "description": "List safe simulated public demo scenarios.",
        "parameters": [],
        "execution_status": "simulation_only",
    },
    "public_release.safety_simulator": {
        "name": "Public Release Safety Simulator",
        "description": "Simulate how public mode refuses risky actions.",
        "parameters": [{"name": "request", "type": "string", "required": True}],
        "execution_status": "simulation_only",
    },
    "public_release.ready_check": {
        "name": "Public Release Ready Check",
        "description": "Summarize release readiness from local hardening checks.",
        "parameters": [],
        "execution_status": "read_only_metadata",
    },
}


def _canonical_id(capability_id: str) -> str:
    normalized = str(capability_id or "").strip()
    return _SCHEMA_ALIASES.get(normalized, normalized)


def capability_to_tool_schema(capability_id: str) -> dict[str, Any] | None:
    canonical = _canonical_id(capability_id)
    schema = _SCHEMAS.get(canonical)
    if schema is None:
        return None
    output = deepcopy(schema)
    output["capability_id"] = canonical
    output["requested_id"] = str(capability_id or "").strip()
    output["permission_summary"] = format_permission_summary_line(canonical)
    return output


def list_tool_schemas() -> list[dict[str, Any]]:
    return [capability_to_tool_schema(capability_id) for capability_id in sorted(_SCHEMAS) if capability_to_tool_schema(capability_id)]


def _format_parameters(parameters: list[dict[str, Any]]) -> list[str]:
    if not parameters:
        return ["- none"]
    lines = []
    for parameter in parameters:
        required = "required" if parameter.get("required") else "optional"
        lines.append(f"- {parameter.get('name')}: {parameter.get('type')} ({required})")
    return lines


def format_tool_schema_preview(capability_id: str) -> str:
    schema = capability_to_tool_schema(capability_id)
    if schema is None:
        return "\n".join(
            [
                "Tool schema preview",
                "",
                f"No schema preview is registered for `{capability_id}`.",
                "This command is metadata-only and did not execute anything.",
            ]
        )
    permission = get_capability_permission(str(schema["capability_id"]))
    return "\n".join(
        [
            "Tool schema preview",
            "",
            f"Capability: {schema['capability_id']}",
            f"Name: {schema['name']}",
            f"Execution status: {schema['execution_status']}",
            f"Risk: {permission.risk_level}",
            schema["permission_summary"],
            "",
            "Description:",
            str(schema["description"]),
            "",
            "Parameters:",
            *_format_parameters(list(schema.get("parameters") or [])),
            "",
            "Scope:",
            "Preview only. No tool was executed and no private runtime data was read.",
        ]
    )


def format_tool_schema_catalog() -> str:
    schemas = list_tool_schemas()
    lines = ["Tool schema catalog", "", f"Count: {len(schemas)}"]
    for schema in schemas:
        lines.append(f"- {schema['capability_id']}: {schema['name']} ({schema['execution_status']})")
    lines.extend(["", "Scope: schema previews only; no execution surface is enabled."])
    return "\n".join(lines)
