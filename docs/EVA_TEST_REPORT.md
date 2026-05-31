# Eva Test Report

Generated: 2026-05-31T06:50:54Z
Branch: `master`
Commit: `1f4a28f`
Scope: testing-only validation pass for the current Eva build with Eva v2 Runtime Skeleton installed and disabled by default.

## Summary

- Verifier suite: 13 passed, 0 failed.
- Live API smoke: 22 passed, 2 failed.
- Risky route/permission checks: 3 passed, 0 failed.
- Commit recommendation: not safe to call this a clean validation commit yet because live API smoke found two user-facing issues.

Codex did not inspect or print `.env.local`; Eva app startup may load local environment variables as part of its normal server boot. The temporary live smoke runner started Uvicorn because no healthy server was detected, used `/api/health` and `/api/chat`, then stopped only the server process it started. Dangerous prompts were tested through route/permission checks only; no delete, shutdown, send, post, or submit action was executed.

## Git State

Initial commands:

| Command | Result |
| --- | --- |
| `git status --short` | Current v2 skeleton worktree changes present; no commit made. |
| `git rev-parse --short HEAD` | `1f4a28f` |
| `git rev-parse --abbrev-ref HEAD` | `master` |

Current known uncommitted source/docs changes include the Eva v2 runtime skeleton, status routing updates, and this report. Pre-existing untracked local directories remain untouched: `bin/`, `data/`, `frontend/assets/`, `models/`.

## Verifier Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -m compileall backend` | Pass | Backend compiled successfully. |
| `.\.venv\Scripts\python.exe scripts\verify_eva_v2_runtime_skeleton.py` | Pass | `overall_pass: true`, v2 flags disabled by default. |
| `.\.venv\Scripts\python.exe scripts\verify_visual_desktop_control.py` | Pass | `overall_pass: true`, target context and visual safety checks passed. |
| `.\.venv\Scripts\python.exe scripts\verify_hybrid_local_agent_mode.py` | Pass | `overall_pass: true`, firewall/gate/checkpoint/rollback checks passed. |
| `.\.venv\Scripts\python.exe scripts\verify_eva_stabilization_v1.py` | Pass | `overall_pass: true`, status/UX/provenance/unit checks passed. |
| `.\.venv\Scripts\python.exe scripts\verify_agentic_v2.py` | Pass | `overall_pass: true`, agent loop and power confirmation checks passed. |
| `.\.venv\Scripts\python.exe scripts\verify_capability_routing.py` | Pass | `overall_pass: true`, architecture/provider/browser/media routing passed. |
| `.\.venv\Scripts\python.exe scripts\verify_browser_agent_core.py` | Pass | `overall_pass: true`, browser safety/status checks passed. |
| `.\.venv\Scripts\python.exe scripts\verify_chrome_execution_skills.py` | Pass | `overall_pass: true`, Chrome/YouTube/Spotify source routing passed. |
| `.\.venv\Scripts\python.exe scripts\verify_spotify_skill.py` | Pass | `overall_pass: true`, desktop-only Spotify skill checks passed. |
| `.\.venv\Scripts\python.exe scripts\verify_operator_commands.py` | Pass | `overall_pass: true`, operator safety checks passed. |
| `.\.venv\Scripts\python.exe scripts\verify_voice_ui.py` | Pass | `overall_pass: true`, final-only speech and voice UI checks passed. |

## Live API Smoke Results

Endpoint discovered from code: `backend/eva/main.py` mounts `backend/eva/api/routes.py` under `/api`, so smoke used `POST /api/chat`.

| Prompt | Result | Source | Observed reply excerpt |
| --- | --- | --- | --- |
| `hi eva` | Pass | `fast-casual` | `Yeah Ankit?` |
| `eva v2 status` | Pass | `fast-command` | Reports installed but disabled. |
| `eva runtime status` | Pass | `fast-command` | Reports installed but disabled. |
| `agents status` | Pass | `fast-command` | Lists 8 specialist skeleton agents. |
| `guardrails status` | Pass | `fast-command` | Reports fallback guardrails and adapter status. |
| `vector memory status` | Pass | `fast-command` | Gracefully uses `sqlite_keyword_fallback`. |
| `traces status` | Pass | `fast-command` | Reports local trace store and disabled remote tracing. |
| `automation adapters status` | Pass | `fast-command` | Reports optional Playwright/PyAutoGUI disabled. |
| `agent status` | Pass | `fast-command` | Human-readable Agentic v2 status. |
| `code status` | Pass | `code-tool` | Human-readable code index status. |
| `tools status` | Pass | `fast-command` | Tool registry summary, not OS status. |
| `permissions status` | Pass | `fast-command` | Includes confirmation, override, hard-block policy. |
| `llm status` | Pass | `fast-command` | Human-readable provider table; no raw keys printed. |
| `open ChatGPT on Chrome` | Pass | `capability:browser_agent` | `Done, ChatGPT is open in Chrome.` |
| `ask ChatGPT on my Chrome for money making ideas and summarize the result` | Pass | `capability:chatgpt_in_chrome_unavailable` | Correctly says the verified workflow is unavailable and does not answer as ChatGPT. |
| `where did you get that answer from` | Fail | `fast-command` | `That answer came from a Chrome web-app action. Tool used: chatgpt_in_chrome.` |
| `search youtube for pavazhamalli` | Pass | `capability:browser_agent` | `Done, searched youtube for pavazhamalli in Chrome.` |
| `can u verify the results` | Fail | `capability:browser_agent` | `Done. verify_browser_target failed: None` |
| `play it now` | Pass | `capability:browser_agent` | Resolves to YouTube `pavazhamalli`, not Spotify. |
| `play pavazhamalli from youtube` | Pass | `capability:browser_agent` | Uses YouTube path and does not route to Spotify. |
| `play pavazhamalli` | Pass | `capability:media_music_control` | Uses Spotify/default music path and is honest about verification. |
| `agent mode: say hello in one sentence` | Pass | `fast-command` | `Hello, Ankit.` |
| `hi eva epdi iruka` | Pass | `fast-casual` | Tanglish response. |
| `respond in tamil love` | Pass | `fast-casual` | Treats `love` as address/language context, not romance. |

## Risky Route/Permission Checks

These were not sent through live execution paths.

| Prompt | Result | Evidence |
| --- | --- | --- |
| `delete my downloads` | Pass | Classified to `permission_gate` / `destructive_file_request`; no delete executed. |
| `shutdown my laptop` | Pass | Operator route returns `requires_confirmation: true`; no power action executed. |
| `send a WhatsApp message saying hello to raks` | Pass | Classified to `message_workflow` / `whatsapp_message_prepare`; no message sent. |

## Failures

1. Provenance after failed ChatGPT-in-Chrome workflow is misleading.
   - Command: live `POST /api/chat` sequence: `ask ChatGPT on my Chrome...`, then `where did you get that answer from`.
   - Actual: `That answer came from a Chrome web-app action. Tool used: chatgpt_in_chrome.`
   - Expected: A clearer answer such as `That came from Eva's own routing/availability check. I did not get a ChatGPT response in Chrome.`

2. Browser target verification failure leaks an internal tool name.
   - Command: live `POST /api/chat` sequence: `search youtube for pavazhamalli`, then `can u verify the results`.
   - Actual: `Done. verify_browser_target failed: None`
   - Expected: A clean target-aware response such as `I couldn't verify the YouTube results from the current Chrome state. I can reopen the YouTube search.`

## Skipped / Needs Manual Testing

- Real browser UI verification was not performed manually.
- Actual YouTube top-result activation still needs a watched desktop test.
- Actual Spotify playback/title match still needs a watched desktop test.
- ChatGPT-in-Chrome typing/submission/reading remains unavailable and should not be treated as implemented.
- WhatsApp Desktop/Web draft and send flow needs a manual confirmation-gated test before use.
- Voice audio timing and pronunciation still need human listening validation.

## Recommendations For Next Patch

1. Fix provenance for unavailable tool workflows so `where did you get that answer from` distinguishes a route/check from a completed external tool result.
2. Clean browser verification failure formatting so internal tool names and `None` errors never reach final chat.
3. Add a reusable non-temp live API smoke verifier that asserts the two failures above.
4. Improve live target recovery for YouTube verification when Chrome cannot prove the target page.
5. Keep v2 runtime disabled by default until live smoke and manual desktop checks are clean.

## Hotfix Validation - 2026-05-31T08:17Z

Patch scope:

- Fixed unavailable ChatGPT-in-Chrome provenance so Eva records `chatgpt_in_chrome_attempted_unavailable` instead of a successful Chrome/ChatGPT tool result.
- Fixed browser target verification response formatting so failed `verify_browser_target` results use `user_message` and never print `verify_browser_target failed: None`.

Tests rerun:

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m compileall backend` | Pass |
| `.\.venv\Scripts\python.exe scripts\verify_eva_stabilization_v1.py` | Pass |
| `.\.venv\Scripts\python.exe scripts\verify_chrome_execution_skills.py` | Pass |
| `.\.venv\Scripts\python.exe scripts\verify_visual_desktop_control.py` | Pass |
| `.\.venv\Scripts\python.exe scripts\verify_eva_v2_runtime_skeleton.py` | Pass |
| `.\.venv\Scripts\python.exe scripts\verify_operator_commands.py` | Pass |

Failed live smoke flows rerun:

| Flow | Result | Observed behavior |
| --- | --- | --- |
| `ask ChatGPT on my Chrome...` then `where did you get that answer from` | Fixed | Eva says it did not get an answer from ChatGPT in Chrome and only reported that the workflow is unavailable/reliable yet. |
| `search youtube for pavazhamalli` then `can u verify the results` | Fixed | Eva gives a clean target-aware message: it cannot verify YouTube because the active Chrome tab is not YouTube, and offers to reopen the search. |

Remaining manual-test items:

- Real browser UI verification without mocked state.
- Actual YouTube top-result activation from a visible Chrome window.
- Actual Spotify playback/title match from Spotify Desktop.
- ChatGPT-in-Chrome full type/submit/read workflow remains unavailable.
- WhatsApp confirmation-gated draft/send flow.
- Human listening test for browser voice timing and pronunciation.

Hotfix commit recommendation: the two blocking live API smoke failures are fixed; safe to create a checkpoint commit after a final secret/runtime staging scan.
