# Eva MCP Policy

Eva's MCP policy is conservative by default: MCP servers may be cataloged for planning, but no MCP server is installed, launched, trusted, or routed to normal chat by catalog presence alone.

## Default Policy

- MCP servers are disabled by default.
- MCP catalog entries are not execution permissions.
- MCP tools must not receive secrets by default.
- MCP tools must not read cookies, tokens, passwords, browser storage, or private files unless a future explicit workflow adds permission gates and user confirmation.
- Repo write, pull request, merge, delete, send, submit, destructive, or system-changing actions require confirmation or override through Eva's existing safety gates.
- Illegal, harmful, credential theft, spying, stealth, persistence, and malware-like requests remain hard-blocked.

## Current MCP Entries

- `official-mcp-servers-registry`: reference-only.
- `github-mcp-server`: experimental, disabled by default.
- `playwright-mcp`: experimental, disabled by default.
- `context7-mcp`: experimental, disabled by default.
- `deepwiki-mcp`: experimental, disabled by default.
- `docker-mcp-registry`: reference-only.
- `awesome-mcp-servers`: reference-only.

## GitHub MCP Notes

GitHub MCP is useful future architecture for repo, issue, and pull request work, but it can read and write remote resources. It must stay disabled until an explicit connector workflow exists with scoped permissions, provenance, confirmation for writes, and secret isolation.

## Playwright MCP Notes

Browser automation MCP can be powerful but risky. It must not read cookies, tokens, localStorage, passwords, payment pages, admin/security forms, or private page content without explicit future safety design and user confirmation.

## Current Boundary Through Phase 6

MCP work remains catalog/policy/status only. Phases after 2.5 added v2 safe execution for existing internal low-risk resources, read-only skill delegation, pending action records, and Safe Code Index v2, but none of that enables MCP execution.

Eva still does not run MCP servers, install packages, execute external MCP tools, enable Playwright/PyAutoGUI execution, send messages, write/delete files, or route normal Eva chat through v2 by default.

Future MCP/connectors work must be permission-gated, provenance-tracked, secret-isolated, and verified before any execution path is enabled.
