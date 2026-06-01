# Eva Resource Registry

This document describes Eva's repo-local resource registry for MCP servers, open-source packages, and existing internal tool surfaces.

The registry is catalog-only unless an existing internal Eva resource is already allowlisted through the current safe surfaces. It does not install packages, run MCP servers, execute external tools, enable Playwright or PyAutoGUI, or route normal Eva chat through the v2 runtime.

## Purpose

- Give Eva a stable place to describe available and candidate resources.
- Keep resource risk decisions explicit before future connector/MCP work.
- Preserve disabled-by-default behavior for Eva v2 flags and optional external tools.
- Provide clean status commands without raw Python dictionaries.

## Key Files

- `backend/eva/resources/models.py`: typed catalog and decision models.
- `backend/eva/resources/open_source_catalog.py`: known open-source and existing Eva resources.
- `backend/eva/resources/mcp_catalog.py`: MCP server catalog entries.
- `backend/eva/resources/allowlist.py`: built-in allowlist, reference-only list, and blocked id markers.
- `backend/eva/resources/risk_policy.py`: policy decision logic.
- `backend/eva/resources/registry.py`: merged lookup/status APIs.
- `backend/eva/resources/status.py`: user-facing formatters.
- `backend/eva/core/fast_commands.py`: read-only status/detail commands.
- `backend/eva/runtime/formatters.py`: v2 preview resource hints.
- `backend/eva/code_index/`: Safe Code Index v2, registered as `eva-code-index`.

## Resource Statuses

- `allowed`: existing low-risk local resource that can be described as available.
- `allowed_with_permission`: existing resource that may touch local, browser, desktop, network, or cloud surfaces and must still use Eva's permission gates.
- `experimental`: cataloged candidate; disabled by default and not executable without a future explicit enablement path.
- `reference_only`: documentation or list entry only; not executable.
- `blocked`: unsafe pattern or explicit policy block.

## Current Catalog Shape

Existing Eva resources include Chrome Execution Skills, Browser Agent Core, Desktop Agent Core, Visual Desktop Control, Spotify Desktop Skill, Workspace Skills, Code Intelligence, Safe Code Index v2, Research SQLite, Memory SQLite, Tavily, NVIDIA NIM, and Ollama.

Candidate/open-source resources include LangGraph, Pydantic AI, LLM Guard, Promptfoo, Langfuse, ChromaDB, Qdrant, Playwright Python, and PyAutoGUI.

MCP entries include the official MCP registry, GitHub MCP Server, Playwright MCP, Context7 MCP, DeepWiki MCP, Docker MCP Registry, and Awesome MCP Servers.

## Status Commands

- `resources status`
- `resource registry status`
- `mcp status`
- `mcp policy status`
- `open source tools status`
- `resource detail <resource_id>`
- `tool resource detail <resource_id>`

All commands are read-only and human-readable. Raw execution is not added by this phase.

## Verification

Run:

```powershell
.\.venv\Scripts\python.exe scripts\verify_eva_resource_registry.py
```

The verifier checks catalog contents, default-disabled MCP behavior, risk decisions, clean status formatting, v2 dry-run resource hints, and absence of package install/network execution code in the registry path.

## Current v2 Boundary

- Explicit v2 commands can use status resources, public browser-open delegation, and read-only delegation for code/research/memory.
- Risky actions can create pending action records through the permission ledger.
- Confirmed risky pending actions still do not execute.
- MCP, Playwright, PyAutoGUI, arbitrary shell, file writes/deletes, and WhatsApp automatic send remain disabled or refused.
- Runtime data produced by resources belongs under ignored paths such as `backend/eva/data/`.
