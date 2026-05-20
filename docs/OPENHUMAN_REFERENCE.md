# OpenHuman Reference Mapping

Eva uses OpenHuman as a product and architecture reference, not as copied source code. OpenHuman is GPL-3.0, so directly copying its implementation would make licensing a deliberate project decision.

## OpenHuman Patterns To Mirror

- Central controller/tool registry with discoverable schemas.
- RPC/WebSocket bridge between UI and local runtime.
- Local memory stored in SQLite-like durable storage.
- Inference provider layer instead of hardcoding one model path.
- Screen intelligence as a controlled module.
- Voice controllers as a separate runtime domain.
- Native desktop shell with safe OS-level capabilities.
- Background channel/runtime loop for external clients.

## Eva Implementation Path

- `backend/eva/tools`: controller-style allowlisted tools.
- `backend/eva/api`: HTTP and streaming bridge for laptop/phone UI.
- `backend/eva/models`: provider layer, currently Ollama.
- `backend/eva/memory`: local SQLite conversation memory.
- `backend/eva/screen`: on-demand screen capture only.
- `backend/eva/voice`: voice-to-voice interfaces reserved for the next phase.
- `frontend`: phone-ready command UI.

## Response Speed Plan

- Done: fast command bypass for greetings/status/help/open-app basics.
- Done: NDJSON streaming endpoint at `/api/chat/stream`.
- Done: frontend renders token chunks as they arrive.
- Next: optional faster local model profile if the user allows an Ollama model download.
- Next: tool-call planner that avoids LLM calls for deterministic desktop actions.
