# Eva Current State

Last updated: 2026-05-26

This is a repo-local handoff for future Codex runs. Treat the working tree as active integration work: inspect files and tests before changing behavior, do not rebuild, and do not undo existing systems.

## Implemented Systems

- Agentic v2: `backend/eva/agent/runner.py`, `backend/eva/agent/planner.py`, `backend/eva/agent/policies.py`, `backend/eva/agent/state.py`, `backend/eva/agent/task.py`, verified by `scripts/verify_agentic_v2.py` and `scripts/verify_agent_runner.py`.
- Laptop operator mode: deterministic command handling in `backend/eva/core/operator_commands.py` and `backend/eva/core/fast_commands.py`, with tools in `backend/eva/tools/registry.py`.
- Desktop Agent Core: desktop observation/window/action helpers in `backend/eva/desktop/` and desktop tools in `backend/eva/tools/desktop.py`, verified by `scripts/verify_desktop_agent_core.py`.
- Browser Agent Core: safe browser status, URL opening, page summaries, link extraction, and research save flow in `backend/eva/browser/`, verified by `scripts/verify_browser_agent_core.py`.
- Code Intelligence v1: safe code indexing/search/feature explanation in `backend/eva/code/`, verified by `scripts/verify_code_intelligence.py`.
- Workspace Skills: safe workspace list/read/search/summary tools in `backend/eva/workspace/`, verified by `scripts/verify_workspace_skills.py`.
- NVIDIA NIM provider: OpenAI-compatible provider in `backend/eva/llm/providers/nvidia_nim.py` with router integration in `backend/eva/llm/router.py`, verified by `scripts/verify_nvidia_nim_provider.py`.
- Research Knowledge SQLite: local research topic/source/note storage in `backend/eva/research/`, defaulting under `backend/eva/data/`, verified by `scripts/verify_research_knowledge.py`.
- Self-diagnostics and provider diagnostics: capability routing in `backend/eva/core/intent_router.py`, diagnostics in `backend/eva/diagnostics/`, and health/provider formatting in `backend/eva/api/routes.py`, verified by `scripts/verify_self_diagnostics.py` and `scripts/verify_capability_routing.py`.
- Tavily web search: search/fallback logic in `backend/eva/tools/tavily_search.py`, verified by `scripts/verify_tavily_search.py`.
- Screen vision: one-shot explicit screenshot analysis in `backend/eva/vision/` and screen tools in `backend/eva/tools/registry.py`, verified by `scripts/verify_screen_vision.py`.
- Memory SQLite: conversation/event/fact storage in `backend/eva/memory/store.py`; runtime database files are ignored.
- Push-to-talk/browser voice UI: frontend voice controls in `frontend/` and Piper status/synthesis in `backend/eva/voice/piper.py`, verified by `scripts/verify_voice_ui.py`.
- Ollama fallback and provider fallback/rate-limit handling: model/provider routers in `backend/eva/models/` and `backend/eva/llm/`, verified by `scripts/verify_llm_router.py` and `scripts/verify_rate_limits.py`.

## Safety Rules

- Do not commit until the user explicitly asks.
- Do not hardcode, print, summarize, or expose API keys or secrets.
- Secrets stay in `.env.local`; do not read or print `.env.local`.
- `.env.local`, `.env`, `*.env`, local SQLite databases, logs, `.venv/`, and `backend/eva/data/` are ignored by `.gitignore`.
- Do not add arbitrary shell execution.
- No camera support.
- No always-on screen watching. Screen capture and vision must stay one-shot and explicit.
- Power actions require explicit confirmation.
- Do not route every issue through fast commands. Prefer capability routing, skill routing, planner/tool integration, and grounded system awareness. Use fast commands only for deterministic controls, safety-critical actions, and lightweight local shortcuts.

## How To Run Eva

From the repo root:

```powershell
cd "C:\Users\HP\Documents\Codex\eva-agent"
.\.venv\Scripts\python.exe -m uvicorn backend.eva.main:app --host 0.0.0.0 --port 8765
```

Or run:

```powershell
.\run.ps1
```

Open locally at:

```text
http://127.0.0.1:8765
```

Open from a phone on the same trusted Wi-Fi at:

```text
http://<laptop-ip>:8765
```

Stop the usual server process with:

```powershell
.\stop.ps1
```

## Key Verification Scripts

Use compile checks plus focused verifiers. The most common baseline is:

```powershell
.\.venv\Scripts\python.exe -m compileall backend
```

Important focused scripts:

- `scripts/verify_llm_router.py`
- `scripts/verify_rate_limits.py`
- `scripts/verify_nvidia_nim_provider.py`
- `scripts/verify_agentic_v2.py`
- `scripts/verify_agent_runner.py`
- `scripts/verify_operator_commands.py`
- `scripts/verify_desktop_agent_core.py`
- `scripts/verify_browser_agent_core.py`
- `scripts/verify_capability_routing.py`
- `scripts/verify_self_diagnostics.py`
- `scripts/verify_research_knowledge.py`
- `scripts/verify_code_intelligence.py`
- `scripts/verify_workspace_skills.py`
- `scripts/verify_screen_vision.py`
- `scripts/verify_voice_ui.py`
- `scripts/verify_tavily_search.py`

## Current Request Flow

`backend/eva/api/routes.py` currently routes chat through these layers:

1. Lightweight deterministic fast commands/responses.
2. Operator commands for safe desktop/browser/system controls.
3. Capability routing through `backend/eva/core/intent_router.py`.
4. Agentic runner for multi-step agentic intents.
5. Planner/tool execution through `ToolCallPlanner`, `ToolExecutor`, and `ToolRegistry`.
6. LLM fallback through cloud/provider router and local Ollama fallback.

## Next Planned Stabilization Task

Stabilize capability-grounded answers and voice parity:

- Make "explain your full architecture" more file-path grounded and request-flow specific.
- Retest OpenRouter provider diagnostics after the OpenRouter/OpenRoute correction.
- Ensure capability questions route through the appropriate skills/tools instead of generic LLM chat.
- Investigate push-to-talk/browser voice bugs where speech stops midway, starts mid-word, speaks different text than the on-screen reply, or mispronounces technical terms.
