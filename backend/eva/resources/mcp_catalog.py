from __future__ import annotations

from .models import EvaResource
from .open_source_catalog import _resource


MCP_RESOURCES = [
    _resource(id="official-mcp-servers-registry", name="Official MCP Servers Registry", category="mcp", provider="Model Context Protocol", kind="mcp_server", homepage="https://modelcontextprotocol.io", requires_network=True, risk_level="low", status="reference_only", notes="Reference catalog only. No server is installed, trusted, or run automatically."),
    _resource(id="github-mcp-server", name="GitHub MCP Server", category="mcp", provider="GitHub", kind="mcp_server", requires_api_key=True, requires_network=True, cloud_capable=True, can_read_files=True, can_write_files=True, can_send_external_messages=False, risk_level="high", status="experimental", notes="May read/write repos through GitHub APIs. Disabled by default; repo write, PR, merge, and delete actions require explicit approval."),
    _resource(id="playwright-mcp", name="Playwright MCP", category="mcp", provider="Microsoft/community", kind="mcp_server", requires_network=True, can_control_browser=True, risk_level="high", status="experimental", notes="Browser-control MCP server. Disabled by default; must not read cookies, tokens, passwords, or storage by default."),
    _resource(id="context7-mcp", name="Context7 MCP", category="mcp", provider="Context7", kind="mcp_server", requires_network=True, cloud_capable=True, risk_level="medium", status="experimental", notes="Documentation/context MCP reference. Disabled by default."),
    _resource(id="deepwiki-mcp", name="DeepWiki MCP", category="mcp", provider="DeepWiki", kind="mcp_server", requires_network=True, cloud_capable=True, risk_level="medium", status="experimental", notes="Repo documentation/context MCP reference. Disabled by default."),
    _resource(id="docker-mcp-registry", name="Docker MCP Registry", category="mcp", provider="Docker", kind="mcp_server", requires_network=True, can_execute_code=True, risk_level="high", status="reference_only", notes="Reference catalog only. Container/server execution is not enabled."),
    _resource(id="awesome-mcp-servers", name="Awesome MCP Servers", category="mcp", provider="community", kind="mcp_server", homepage="https://github.com/punkpeye/awesome-mcp-servers", requires_network=True, risk_level="medium", status="reference_only", notes="Community list; not trusted by default and never auto-installed."),
]


def get_mcp_resources() -> list[EvaResource]:
    return list(MCP_RESOURCES)
