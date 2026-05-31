# Eva Bug Queue

Last updated: 2026-05-26

Use this queue as a stabilization handoff. Before fixing, reproduce from the current repo and prefer capability routing, skill routing, planner/tool integration, and grounded system awareness over broad fast-command patches.

## EVA-001: Architecture answer still needs more grounding

- command: `explain your full architecture`
- actual: Improved answer, but it can still be too high-level and may omit concrete file paths and the real request flow.
- expected: Eva should explain the active architecture with concrete files such as `backend/eva/api/routes.py`, `backend/eva/core/intent_router.py`, `backend/eva/tools/registry.py`, `backend/eva/agent/runner.py`, `backend/eva/llm/router.py`, `backend/eva/memory/store.py`, `backend/eva/browser/`, `backend/eva/desktop/`, `backend/eva/research/`, `backend/eva/code/`, `backend/eva/vision/`, and `frontend/`.
- likely area: `backend/eva/core/intent_router.py`, `backend/eva/api/routes.py`, `backend/eva/diagnostics/health.py`, `backend/eva/code/`, `scripts/verify_capability_routing.py`, `scripts/verify_self_diagnostics.py`.

## EVA-002: Voice sometimes stops midway

- command: Use browser push-to-talk or voice playback for a medium/long Eva answer.
- actual: Speech sometimes stops before the full assistant response is spoken.
- expected: Speech should continue until the displayed assistant reply is fully spoken or until the user intentionally stops it.
- likely area: `frontend/app.js`, `frontend/index.html`, `frontend/styles.css`, `backend/eva/api/routes.py` TTS endpoints, `backend/eva/voice/piper.py`, `scripts/verify_voice_ui.py`.

## EVA-003: Voice sometimes starts from the middle or inside a word

- command: Trigger voice playback for a fresh Eva response, especially after previous playback or interruption.
- actual: Speech can begin mid-response or inside a word.
- expected: Speech should start at the first character/word of the current assistant reply.
- likely area: frontend speech queue/state management in `frontend/app.js`, browser SpeechSynthesis handling, push-to-talk state transitions, `scripts/verify_voice_ui.py`.

## EVA-004: Voice sometimes speaks different text than the screen

- command: Ask Eva a prompt that renders text on screen and triggers voice playback.
- actual: Spoken text can differ from the displayed assistant response.
- expected: TTS should speak the exact current assistant reply or a clearly intentional sanitized version of it.
- likely area: `frontend/app.js` response streaming/TTS coupling, `/api/chat/stream` events in `backend/eva/api/routes.py`, `backend/eva/voice/piper.py`, `scripts/verify_voice_ui.py`.

## EVA-005: Technical terms are pronounced badly

- command: Ask Eva to speak text with terms such as `OS`, `.exe`, `C:\Users\HP\Documents`, `OpenRouter`, `NVIDIA NIM`, or Windows paths.
- actual: TTS pronounces technical terms and paths awkwardly.
- expected: Voice output should normalize common technical tokens into speakable text without changing the on-screen reply.
- likely area: TTS text normalization in `frontend/app.js` and/or `backend/eva/voice/piper.py`; add coverage to `scripts/verify_voice_ui.py`.

## EVA-006: OpenRouter/OpenRoute confusion needs retest

- command: `test OpenRouter API` and `openrouter API is built in within u`
- actual: Confusion with OpenRoute/OpenRouteService was patched through diagnostics, but should be retested against the current routing stack.
- expected: OpenRouter should route to provider diagnostics; OpenRoute/OpenRouteService map-routing concepts should not be confused with Eva's LLM provider.
- likely area: `backend/eva/core/intent_router.py`, `backend/eva/diagnostics/providers.py`, `backend/eva/api/routes.py`, `scripts/verify_capability_routing.py`, `scripts/verify_self_diagnostics.py`.

## EVA-007: Some capability questions may fall through to generic LLM chat

- command: Ask capability questions such as `what systems do you have`, `what page am I on`, `what window am I on`, `where is browser agent implemented`, or `what do we know about NVIDIA NIM`.
- actual: Some questions may still be answered by generic LLM chat instead of grounded skills/tools.
- expected: Capability questions should route to deterministic diagnostics, capability routes, agentic skills, or safe tools as appropriate, with file/tool/source grounding where relevant.
- likely area: `backend/eva/core/capabilities.py`, `backend/eva/core/intent_router.py`, `backend/eva/api/routes.py`, `backend/eva/core/fast_commands.py`, `backend/eva/agent/policies.py`, `backend/eva/tools/registry.py`, `scripts/verify_capability_routing.py`.
