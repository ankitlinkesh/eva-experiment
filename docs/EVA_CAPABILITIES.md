# Eva Capabilities

Eva capabilities are local metadata records that describe what an existing Eva system can do, how risky it is, and which verifier covers it. They are discovery and planning inputs, not a broad execution switch.

## Capability Model

Each capability records:

- id and name
- provider and category
- risk level
- read-only or local-write mode
- confirmation requirement
- default enabled status
- safety notes
- verifier name when available

The safe catalog currently covers existing Research Memory, explicit Eva v2 preview/status paths, and public release/demo/status surfaces.

## Permissions

The permission matrix explains whether a capability is read-only, an explicit local write, confirmation-gated, or blocked by default. External sending, browser control, desktop control, MCP execution, Playwright, PyAutoGUI, arbitrary shell, and destructive file actions remain disabled or future-gated.

Commands:

- `eva capability permissions`
- `eva capability permission <capability_id>`

## Resource Mapping

Phase 9D adds a metadata-only bridge:

Capability -> Permission decision -> Resource -> Provider or agent -> Tool schema preview -> Execution availability -> Safety notes

This helps future Planner v3 answer:

- which capability fits a goal
- which resource backs it
- whether it is allowed
- whether it is available now, preview-only, disabled experimental, or reference-only
- which agent would handle it later

Commands:

- `eva capability resolve <capability_id>`
- `eva capability resources <capability_id>`
- `eva resource capabilities <resource_id>`
- `eva capability resource matrix`
- `eva capabilities available`
- `eva capabilities preview only`
- `eva capabilities blocked`
- `eva capability plan resources <goal text>`

## Tool Schema Previews

Tool schema previews describe parameters and execution class for safe existing capabilities. They do not execute tools.

Commands:

- `eva capability schema <capability_id>`
- `eva tool schema preview <capability_id>`
- `eva tool schemas`

## Public vs Private Mode

Public/community mode keeps high-risk systems disabled. Private/local development may expose more metadata, but Phase 9D does not enable risky execution in either mode.

Current non-enabled surfaces:

- MCP execution
- Playwright execution
- PyAutoGUI execution
- browser control
- screen watching
- WhatsApp sending
- arbitrary shell
- cloud embeddings
- default vector search
- normal-chat routing through Eva v2

## Examples

`eva capability resolve research_memory.retrieve` shows the Research Memory resource, permission status, ResearchAgent ownership, schema-preview availability, and `available_read_only` status.

`eva capability resolve research_memory.vector_search` shows that the vector index resource is experimental and disabled by default. Lexical Research Memory retrieval remains primary.

`eva resource capabilities eva-research-memory-v2` lists the capabilities backed by the local Research Memory v2 store.

## Scope

This layer is metadata-only. It does not install packages, run servers, call cloud APIs, read secret files, control browsers/desktops, send messages, delete files, or execute MCP tools.
