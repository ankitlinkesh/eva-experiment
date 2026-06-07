# Eva Threat Model

This document summarizes the current safe public posture for Eva as the project moves toward an AI operating layer for a laptop.

## Current Boundary

Eva may use API-backed LLM reasoning when configured, but local runtime data stays local by default. normal chat is not routed through v2 by default. Explicit v2 commands can preview routes, plans, dry-runs, and selected read-only delegation surfaces.

Capability discovery is metadata-only. It does not enable MCP execution, Playwright execution, PyAutoGUI execution, WhatsApp sending, browser control, screen watching, arbitrary shell execution, package installs, cloud embeddings, or silent file modification.

## Protected Assets

- User secrets, including .env.local values.
- API keys, bearer tokens, cookies, passwords, and session data.
- Local research memory, local task traces, pending action ledgers, runtime caches, and local databases.
- Browser account state, private pages, chats, email contents, paywalled content, and form fields.
- Desktop state, screenshots, screen observations, and app contents.

## Trust Boundaries

User commands are trusted as task intent, but they are not automatic permission grants for risky actions.

External web pages, retrieved research, copied text, browser page contents, imported notes, and model outputs are untrusted content as data. Eva must not treat them as instructions to bypass safety gates or expose secrets.

Cloud LLM providers are optional reasoning services. Local context sent to them must be minimized and redacted first. Raw screenshots, raw files, private chats, credentials, cookies, tokens, and passwords are not sent by default.

## Default Refusals

Eva refuses or leaves disabled by default:

- MCP tool execution.
- Playwright and PyAutoGUI execution.
- Always-on screen watching.
- Raw coordinate clicking.
- WhatsApp, email, or social message sending without a future explicit confirmation workflow.
- Destructive file actions without a future override-gated executor.
- Arbitrary shell execution.
- Credential access, token extraction, cookie access, password reading, stealth, persistence, exfiltration, and malware-like behavior.

## Permission Expectations

Read-only status, planning, discovery, safe local research retrieval, and demo simulation can be public-safe.

Scoped local writes, such as importing a user-provided research note or exporting sanitized research notes, require explicit commands and must not run as background writes.

Destructive local actions, external sends, browser or desktop control, and system-changing actions require future permission-gated executor phases before they can run.

## Capability System Role

The capability registry, permission matrix, and tool schema previews are discovery surfaces. They help Eva explain what exists, what is public-safe, what needs confirmation, and what is blocked. They do not add new execution behavior.
