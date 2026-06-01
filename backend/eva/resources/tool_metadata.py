from __future__ import annotations


RESOURCE_TOOL_POLICY = {
    "catalog_only": True,
    "installs_packages": False,
    "runs_mcp_servers": False,
    "executes_external_tools": False,
    "reads_secrets": False,
}


def resource_tool_policy_summary() -> str:
    return "Resource registry is catalog-only: no installs, no MCP server runs, no external execution, and no secret reads."
