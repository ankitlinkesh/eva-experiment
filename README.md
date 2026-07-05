# Eva Agent

Eva is a source-available, local-first desktop AI agent foundation built with Python, FastAPI, and a browser-based command center. It combines deterministic commands, bounded planning, capability metadata, local memory foundations, and explicit safety gates.

Eva is not presented as an unrestricted autonomous operator. The public demo is designed to show what is implemented, what remains locked, and which evidence should be refreshed before a release decision.

## What Is Eva?

- A modular foundation for local laptop-assistant workflows.
- A deterministic command system with human-readable status and refusal paths.
- A bounded planner and agent loop with stop, verification, and risk-review concepts.
- A capability registry with permission, resource, schema, and verifier metadata.
- A local/mock-first architecture for demonstrating future browser, desktop, voice, coding, and research workflows safely.

## Current Verified Status

The repository contains the Phase 29 Public Demo / Release profile. It is report/status/documentation only and is considered ready for local demo review only after the focused, quick, and full verifier commands below pass in the current checkout.

No publication, upload, package release, installer creation, commit, tag, or push is performed by Phase 29.

## Capabilities

- FileAgent inspection, drafts, approval metadata, and sandbox previews.
- Phase 12L narrow approved creation of one new `.md` or `.txt` file under `docs/` or `samples/`.
- Bounded planner, agent-loop, workflow, context, threat-defense, and memory previews.
- Browser public-URL read-only observation reports; browser control remains locked.
- One-shot redacted desktop observation reports; desktop control remains locked.
- Desktop-control policy and dry-run gate reports without real control.
- News/Web Intelligence local/mock or safe-read-only reports.
- CodingAgent classification, patch-plan, review, test-plan, risk, and handoff previews without source editing.
- Voice Assistant locked/mock foundation without microphone or audio execution.

## Demo Commands

```text
eva release status
eva release demo
eva release commands
eva release capability map
eva release safety proof
eva release readiness
eva release limitations
eva release verification
```

These commands return deterministic local text. They do not publish, execute tools, inspect private sessions, or unlock restricted features.

Additional established safety demonstrations remain available:

```text
eva public checklist
eva public hardening status
eva demo scenarios
eva demo run whatsapp-confirmation
eva safety test read .env.local
eva doctor public
```

## Run Locally

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.eva.main:app --host 0.0.0.0 --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

Private settings can be created from `.env.example`. Never commit or display private environment files.

## Verification

Run the Phase 29 verifier:

```powershell
.\.venv\Scripts\python.exe scripts\verify_eva_public_demo_release.py
```

Run both master profiles:

```powershell
.\.venv\Scripts\python.exe scripts\verify_eva_all.py --quick --timeout 90
.\.venv\Scripts\python.exe scripts\verify_eva_all.py --full --timeout 90
```

Finish with:

```powershell
git diff --check
git status --short
```

These commands provide local evidence only. They do not publish or certify production security.

## Safety Boundaries

- No unrestricted shell or arbitrary command execution.
- No browser clicking, typing, login, upload, download, cookie, profile, or session control.
- No desktop clicking, typing, hotkeys, clipboard, app/window control, or continuous monitoring.
- No unrestricted crawler.
- No CodingAgent source editing or patch application.
- No public-demo live LLM/API/provider call.
- No cloud or MCP execution.
- No microphone, audio recording, playback, ASR, or TTS execution in the voice foundation.
- No secret, configuration, session, raw memory database, or private WorkSession dump exposure.
- No broad filesystem mutation.
- Phase 12L narrow approved text-file creation remains the only real write path.

## Known Limitations

- The public demo is a local report/status profile, not a hosted service.
- Browser and desktop backends may report unavailable while preserving safe mock/status behavior.
- News is local/mock or safe-read-only; it is not unrestricted web crawling.
- CodingAgent creates plans and reviews only.
- Voice remains a locked/mock foundation.
- Verification evidence is checkout-specific and must be refreshed before release review.
- Phase 29 does not create a release candidate, commit, tag, installer, package, or upload.

## Non-Goals

- Unrestricted autonomy or self-modifying code.
- Silent background monitoring.
- Production-security certification.
- Automatic publication or deployment.
- Automatic messaging, purchasing, submitting, or destructive file actions.
- Claims that locked or preview-only features are real execution capabilities.

## License

Eva is source-available under the PolyForm Noncommercial License 1.0.0.

Non-commercial use is allowed. Commercial use, resale, paid redistribution, hosted commercial services, or selling modified versions requires separate written permission from the author.
