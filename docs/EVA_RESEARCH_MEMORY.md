# Eva Research Memory

## Overview

Eva Research Memory is the local saved-research system for Eva. It stores sanitized notes, topics, tags, source metadata, quality signals, and retrieval metadata in local runtime data.

Research Memory data is local runtime data. Eva may still use API-backed LLM providers elsewhere when configured, so this document only describes the Research Memory storage and command surface.

For public/community releases, Eva is source-available under the PolyForm Noncommercial License 1.0.0. Public release artifacts must not include `.env`, `.env.local`, API keys, personal Research Memory database files, screenshots, private browser/session data, local model files, or runtime traces.

## Current Capability Summary

- Research Memory v2 local note store with clean status, recent, topics, save, search, and topic-summary output.
- Import/export/cleanup utilities for local notes.
- Tags, quality warnings, duplicate preview, and filtered search.
- Optional vector-search preparation with a lightweight local fallback for tests.
- Lexical-first hybrid retrieval with topic, tag, source filters, quality scoring, small recency scoring, duplicate/low-quality penalties, and diversity reranking.
- Recall statistics, promotion candidate preview, ranking explanations, and memory review commands.
- Explicit v2 context injection for prompts that ask to use saved/local research memory.
- Human-readable help, command reference, examples, safety notes, and phase summary commands.

## Command Reference

Core:

- `research memory status`
- `research memory recent`
- `research memory topics`
- `research memory stats`

Save/import:

- `research memory save topic <topic> note <text>`
- `research memory save topic <topic> tags <tag1,tag2> note <text>`
- `research memory import note topic <topic> title <title> text <text>`
- `research memory import note topic <topic> title <title> tags <tag1,tag2> text <text>`

Search/retrieve:

- `research memory search <query>`
- `research memory search <query> topic <topic>`
- `research memory search <query> tag <tag>`
- `research memory search <query> source <source_type>`
- `research memory retrieve <query>`
- `research memory retrieve <query> topic <topic>`
- `research memory retrieve <query> tag <tag>`
- `research memory retrieve <query> source <source_type>`
- `research memory retrieval status`
- `research memory retrieval plan <query>`
- `research memory ranking status`
- `research memory recall stats`
- `research memory promote candidates`
- `research memory review memory`

Topics/tags/quality:

- `research memory topic <topic>`
- `research memory tags`
- `research memory duplicates`
- `research memory merge duplicates preview`
- `research memory quality`

Import/export/cleanup:

- `research memory export`
- `research memory export topic <topic>`
- `research memory delete item <item_id>`
- `research memory clear topic <topic> confirm`

Vector prep:

- `research memory vector status`
- `research memory vector index preview`
- `research memory vector search <query>`
- `research memory semantic search <query>`

Help:

- `research memory help`
- `research memory commands`
- `research memory examples`
- `research memory safety`
- `research memory phase summary`

## Examples

Save notes:

- `research memory save topic Eva note Research Memory keeps saved research local.`
- `research memory save topic Eva tags memory,safety note Vector search is disabled by default.`

Import notes:

- `research memory import note topic Eva title Memory safety text Research Memory refuses private scraping.`
- `research memory import note topic Eva title Retrieval tags memory,retrieval text Lexical retrieval is the default.`

Search/retrieve:

- `research memory search Eva`
- `research memory search Eva tag memory`
- `research memory retrieve Eva`
- `research memory retrieval plan Eva`
- `research memory ranking status`
- `research memory promote candidates`

Review and cleanup:

- `research memory topics`
- `research memory tags`
- `research memory review memory`
- `research memory quality`
- `research memory duplicates`
- `research memory promote candidates`
- `research memory clear topic Test confirm`

Explicit v2 usage:

- `eva v2 plan use my saved research about Eva memory`
- `eva v2 dry run summarize what I saved about Eva`
- `eva v2 execute research memory retrieve Eva`

## Safety Model

Research Memory:

- Stores local sanitized notes.
- Uses lexical retrieval by default.
- Has vector search prepared but disabled by default.
- Uses diversity reranking to reduce repeated/near-duplicate results.
- Uses small recency scoring without hiding older notes.
- Stores recall stats as hashed query references, not raw queries.
- Keeps promotion candidates preview-only.
- Does not use cloud embeddings.
- Does not use cloud summarization.
- Does not import or require MemOS, Redis, sqlite-vec, Ollama embeddings, or package installs.
- Does not enable background dreaming, auto-reflection, auto-promotion, auto-memory writes, or auto-delete.
- Does not scrape private, logged-in, Gmail, chat, or paywall pages.
- Does not read cookies, tokens, localStorage, sessionStorage, or passwords.
- Does not read `.env.local`.
- Does not expose full memory dumps through v2.
- Does not support clear-all.
- Keeps delete item-scoped.
- Requires `confirm` for topic clear.
- Keeps exports under local runtime export storage and normal output shows the filename only.

## Storage Model

Research Memory uses a local runtime SQLite store. Normal user-facing output says "local runtime SQLite store" and does not print full internal storage paths.

Saved text is sanitized before storage when it looks secret-like or private. Search and retrieval output is summary-oriented and avoids internal rows, Python object reprs, stack traces, and vector payloads.

## v2 Integration

Research Memory integrates with explicit v2 route, plan, dry-run, and read-only execution paths.

Examples:

- `eva v2 plan use my saved research about Eva memory`
- `eva v2 dry run summarize what I saved about Eva`
- `eva v2 execute research memory retrieve Eva`

Normal Eva chat is not routed through v2 by this phase. v2 context injection only appears when the user explicitly asks to use saved/local research memory.

## Vector Search Status

Vector search is disabled by default. The current interface is a local-first preparation layer with a lightweight hashing fallback for tests and future plumbing.

Chroma/Qdrant are not active yet. No cloud embedding or cloud summarization path is enabled.

Lexical search and hybrid retrieval remain the default practical retrieval behavior.

## Ranking and Review

Phase 9C adds a local, dependency-free ranking upgrade inspired by memory-system architecture ideas. It does not copy code from MemOS and does not add MemOS as a dependency.

Ranking behavior:

- Base lexical relevance remains strongest.
- Quality score provides a medium boost.
- Recency provides only a small deterministic boost.
- Duplicate-like and low-quality notes are deprioritized, not deleted.
- Diversity reranking reduces repeated/near-duplicate results.
- Retrieval output includes short match/ranking reasons.

Recall stats:

- Recall count is updated only after selected retrieval results are returned.
- Query references are stored as SHA-256 hashes of normalized queries.
- Normal output shows recall counts and last recalled time, not raw query strings.

Promotion and review:

- `research memory promote candidates` is preview-only.
- `research memory review memory` summarizes item count, low-quality notes, duplicate-like groups, top recalled items, promotion candidates, and safe next commands.
- No promotion, deletion, merge, reflection, or write runs automatically.

## Limitations

- Vector search is experimental and disabled unless explicitly enabled for local testing.
- Semantic quality is not production-grade without a future local vector backend.
- Research Memory does not browse or scrape private pages.
- Research Memory does not replace general Eva LLM reasoning.
- Confirmed risky actions still depend on Eva's broader permission-gated execution phases.

## Future Roadmap

- Optional local vector backend integration after safety and storage policies are stable.
- Better topic summaries from local data without cloud summarization by default.
- More precise source-type filters and import helpers.
- UI display improvements for tags, quality warnings, and duplicate previews.
- Continued v2 integration while keeping normal chat routing unchanged.
