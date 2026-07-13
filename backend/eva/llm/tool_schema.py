from __future__ import annotations

from typing import Any


def to_openai_tools(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert registry planner specs (each: name, description, args_schema)
    into OpenAI function-tool format."""
    tools = []
    for spec in specs:
        name = spec.get("name")
        if not name:
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": spec.get("description", ""),
                "parameters": spec.get("args_schema") or {"type": "object", "properties": {}},
            },
        })
    return tools
