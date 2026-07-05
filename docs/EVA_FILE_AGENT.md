# Eva FileAgent v1

FileAgent v1 is Eva's read-only, repo-scoped file inspection foundation.

It helps Eva understand safe project files without becoming a file editor, shell, desktop controller, or background watcher.

Phase 12B adds read-only content understanding and project inventory. These are deterministic local heuristics, not cloud or LLM summaries.

Phase 12C adds draft preview mode. Drafts and diffs are shown in chat output only. No file is created or modified.

Phase 12D adds apply-readiness planning. It can explain whether a draft would be eligible for a future confirmed apply, what confirmation phrase would be required, what backup/checkpoint plan would be needed, how rollback would work, and how a future write should be verified. It still does not write files or create backups.

Phase 12E adds an approval ledger and deferred apply queue. It can create local metadata records for future apply requests, track pending/approved/denied/cancelled/expired states, record audit-style events, and validate exact confirmation phrases. Approval does not apply files.

Phase 12L adds the first narrow real apply gate. It can create one brand-new safe `.md` or `.txt` file directly under `docs/` or `samples/` only after an approved FileAgent record and the exact phrase `confirm real create <approval_id>`. It cannot edit, overwrite, append, delete, move, rename, copy, or write source/config/runtime files.

Phase 12O adds project inspection and reality-check workflow surfaces. They reuse FileAgent inventory and workflow-state metadata to answer "inspect this project", "what proof do we have", "what is broken", and "what should we do next" without applying changes or running verifiers.

## Available Commands

- `eva file status`
- `eva file inspect <path>`
- `eva folder inspect <path>`
- `eva file search <query>`
- `eva file preview <path>`
- `eva file understand <path>`
- `eva file summarize <path>`
- `eva project structure`
- `eva project structure <path>`
- `eva file explain <path>`
- `eva project inventory`
- `eva project inventory <path>`
- `eva project explain`
- `eva project explain <path>`
- `eva project missing`
- `eva project key files`
- `eva project dependencies`
- `eva file draft create <path> text <text>`
- `eva file draft append <path> text <text>`
- `eva file draft replace <path> old <old_text> new <new_text>`
- `eva file draft diff <path> text <proposed_full_content>`
- `eva draft readme section <topic>`
- `eva draft project summary`
- `eva draft report outline <title>`
- `eva draft project todo`
- `eva file apply policy`
- `eva file apply readiness create <path> text <text>`
- `eva file apply readiness append <path> text <text>`
- `eva file apply readiness replace <path> old <old_text> new <new_text>`
- `eva file write safety <path>`
- `eva file rollback plan <path>`
- `eva file approval status`
- `eva file approval request create <path> text <text>`
- `eva file approval request append <path> text <text>`
- `eva file approval request replace <path> old <old_text> new <new_text>`
- `eva file approvals pending`
- `eva file approval <approval_id>`
- `eva file approval approve <approval_id> confirm <exact_phrase>`
- `eva file approval deny <approval_id>`
- `eva file approval cancel <approval_id>`
- `eva file approval events <approval_id>`
- `eva file approvals expire`
- `eva project inspect`
- `eva project reality check`
- `eva project recent changes`
- `eva project next step`
- `eva project proof`
- `eva done check`

## Allowed Behavior

FileAgent v1 can:

- inspect safe file or folder metadata
- list a bounded number of folder entries
- search filenames only inside the repo/project scope
- preview safe text, code, markdown, JSON, YAML, TOML, CSV, and config-example files with size limits
- summarize safe text/code/docs files with deterministic local heuristics
- detect headings, imports/dependency hints, Python symbols, TODOs, and shallow config types
- build a bounded project inventory
- detect common key files, dependency/config files, docs, tests, and likely project type
- show a missing-file checklist for common docs/configs
- show a bounded project structure summary
- generate proposed file content as output-only draft previews
- generate append, replace, and unified diff previews without applying them
- draft README sections, project summaries, report outlines, and project TODO recommendations in chat output only
- validate draft targets/content for secret-like text, sensitive paths, runtime folders, huge content, and binary-looking content
- evaluate whether a draft is eligible for future confirmed apply
- show a future confirmation phrase such as `confirm apply file draft <path>`
- generate backup/checkpoint, rollback, and verification plans for future write phases
- create local approval metadata for future apply only
- track approval ledger states: pending, approved_for_future_apply, denied, cancelled, expired, blocked, and consumed_future_apply
- record audit-style approval events without deleting denied/cancelled records
- provide planner, capability, resource, and schema metadata for future routing

## Refused Behavior

FileAgent v1 refuses:

- all file writes except the Phase 12L create-new-text-file gate
- existing-file edits, overwrites, appends, deletes, moves, renames, and copies
- whole-drive scans
- `.env.local`, `.env`, secret, token, cookie, password, private-key, browser-profile, and credential-like paths
- runtime databases and generated data under ignored runtime folders
- binary/database preview
- OCR, PDF parsing, DOCX parsing, cloud summarization, and embeddings
- MCP, Playwright, PyAutoGUI, browser control, screen watching, package installs, arbitrary shell, and planner task execution

Draft mode also refuses sensitive targets such as `.env`, secret/token/cookie/session paths, runtime data folders, and generated data paths. If secret-like text appears in draft content, normal output redacts it and warns.

Apply-readiness mode does not accept confirmation phrases as execution. It only shows what a future safe apply flow would require.

Approval mode accepts exact confirmation phrases only to mark a ledger record as `approved_for_future_apply`. It does not apply the change, create a backup, restore a file, or consume the approval.

## Integration

FileAgent v1 is registered as:

- agent: `FileAgent`
- resource: `eva-file-agent-v1`
- capabilities:
  - `file.inspect_path`
  - `file.list_folder`
  - `file.search_name`
  - `file.preview_text`
  - `file.explain_project_structure`
  - `file.understand_text`
  - `file.summarize_text`
  - `file.project_inventory`
  - `file.project_explain`
  - `file.project_missing`
  - `file.project_dependencies`
  - `file.draft_create_preview`
  - `file.draft_append_preview`
  - `file.draft_replace_preview`
  - `file.diff_preview`
  - `file.draft_readme_section`
  - `file.draft_project_summary`
  - `file.draft_report_outline`
  - `file.draft_project_todo`
  - `file.apply_readiness`
  - `file.write_safety_policy`
  - `file.rollback_plan`
  - `file.verification_plan`
  - `file.approval_status`
  - `file.approval_request_create`
  - `file.approval_list_pending`
  - `file.approval_view`
  - `file.approval_approve_future`
  - `file.approval_deny`
  - `file.approval_cancel`
  - `file.approval_events`
  - `file.approval_expire`
  - `file.apply_executor_status`
  - `file.sandbox_apply_policy`
  - `file.sandbox_apply_approved`
  - `file.sandbox_verify_apply`
  - `file.sandbox_rollback_apply`
- verifier: `scripts/verify_eva_file_agent_readonly.py`
  and `scripts/verify_eva_file_agent_understanding.py`
  and `scripts/verify_eva_file_agent_draft_preview.py`
  and `scripts/verify_eva_file_agent_write_safety.py`
  and `scripts/verify_eva_file_agent_sandbox_apply.py`

The capability and tool-schema entries are metadata/discovery surfaces. They do not enable write execution or normal-chat v2 routing.

## Draft Preview Roadmap

Future write mode would need exact user confirmation, backup/checkpoint creation, diff review, verification, and rollback planning. Phase 12D designs those requirements but does not implement the executor.

## Phase 12D Apply-Readiness

Apply-readiness reports include:

- future eligibility decision
- required confirmation phrase
- diff review requirement
- backup/checkpoint plan
- rollback plan
- verification checklist
- blockers for sensitive paths, unsafe content, unsupported operations, or large changes

No file writes are enabled in Phase 12D. No backups are created. No rollback is performed. This phase only plans future safe apply behavior.

## Phase 12E Approval Ledger

The approval ledger is a Jarvis-inspired authority and audit concept implemented in Eva-native code. It stores local metadata records under ignored runtime storage.

Approval records include:

- approval id
- operation and safe repo-relative path
- required confirmation phrase
- status and expiration time
- safety summary
- redacted bounded diff preview when safe
- warnings and blockers
- audit events

Approval states:

- pending
- approved_for_future_apply
- denied
- cancelled
- expired
- blocked
- consumed_future_apply

Phase 12E still does not apply files. An approved record is only a future-apply readiness signal. A future apply phase must re-check path policy, re-check content safety, create backup/checkpoint, apply the approved diff, verify by reading back the target, and keep rollback available.

## Phase 12F Sandbox Apply Harness

Phase 12F adds an apply executor contract and sandbox harness. It proves the lifecycle:

1. build an apply request from an approved FileAgent approval record
2. re-check authority and safety
3. map the target to an ignored runtime sandbox name
4. create a sandbox-only backup/checkpoint
5. apply the approved draft content only inside the sandbox
6. verify sandbox content by local readback/hash comparison
7. roll back sandbox state from the sandbox checkpoint
8. record sandbox lifecycle events in the approval ledger

Commands:

- `eva file apply executor status`
- `eva file apply sandbox policy`
- `eva file approval sandbox apply <approval_id>`
- `eva file approval sandbox verify <approval_id>`
- `eva file approval sandbox rollback <approval_id>`

Sandbox apply may write only under ignored FileAgent runtime sandbox storage. It does not use the original target path directly, does not copy secret files, does not read blocked paths, and does not perform delete, move, rename, or broad filesystem operations.

No real project or user file is created, modified, backed up, restored, or applied in Phase 12F. Approval is still not real execution. Real apply remains future permission-gated work.

## Phase 12G Natural Routing And Authority

Phase 12G adds Eva's global AuthorityDecision summary and the `eva ask <request>` wrapper. FileAgent remains the domain enforcer; the global authority layer only summarizes whether a request is read-only, draft-only, approval-only, sandbox-only, blocked, or refused.

Natural examples:

- `eva ask inspect this project`
- `eva ask show pending approvals`
- `eva ask draft a README section about FileAgent`
- `eva ask sandbox apply the approved change`
- `eva ask verify the sandbox apply`
- `eva ask rollback the sandbox apply`

For sandbox apply/verify/rollback, `eva ask` uses the existing FileAgent sandbox executor only when an approval id is explicit or exactly one sandbox-eligible approved record exists. If none or multiple records exist, Eva asks for a specific approval id instead of guessing.

Phase 12G does not enable real FileAgent apply. Real project/user file writes, edits, deletes, moves, copies, real backups, and real restores remain disabled.

## Phase 12H Control Center View

Phase 12H surfaces FileAgent state inside Eva Control Center v1. The dashboard shows:

- FileAgent read-only inspection and project inventory availability
- draft preview availability
- approval ledger counts
- sandbox apply/verify/rollback harness status
- the boundary that real apply is create-new-text-file only

Dashboard and commands:

- `/control`
- `/control/status.json`
- `eva control center status`
- `eva dashboard url`
- `eva ask show control center`

This is status-only. The dashboard does not create approval requests, approve records, run sandbox apply, open a browser, or modify real project/user files.

## Phase 12L Narrow Real Apply Gate

Phase 12L adds Eva's first tightly controlled real file apply path. It is not broad file editing.

Allowed:

- create one new `.md` or `.txt` file
- target must be directly under `docs/` or `samples/`
- target must not already exist
- approval record must already be `approved_for_future_apply`
- exact phrase required: `confirm real create <approval_id>`
- created content is read back and verified by hash
- rollback can remove only the unchanged Eva-created file with `confirm rollback real create <approval_id>`

Blocked:

- editing or overwriting existing files
- `.py`, `.json`, `.toml`, `.yaml`, `.yml`, `.env`, config, lockfile, database, binary, image, PDF, DOCX, XLSX writes
- source/runtime/config folders such as `backend/`, `scripts/`, `.git/`, `.venv/`, `node_modules/`, and `backend/eva/data/`
- delete, move, rename, broad apply, absolute paths, path traversal, hidden files, and secret-like content

Commands:

- `eva file real apply policy`
- `eva file real apply eligibility <approval_id>`
- `eva file approval real create <approval_id> confirm real create <approval_id>`
- `eva file approval real verify <approval_id>`
- `eva file approval real rollback <approval_id> confirm rollback real create <approval_id>`
- `eva file real apply status`

Natural route:

- `eva ask create the approved text file`
- `eva ask really create the approved docs file`
- `eva ask apply the approved docs file for real`
- `eva ask confirm real create <approval_id>`
- `eva ask confirm rollback real create <approval_id>`
- `eva ask what real actions can Eva do now`

Commands remain debug/fallback surfaces. The natural-language-first path is through `eva ask`, but exact confirmation phrases are still required. No paid tools or new dependencies are needed.

## Phase 12J Golden Workflow Polish

FileAgent now backs the `safe_project_note_create` golden workflow. The workflow is orchestration only:

1. Interpret a natural project-note request.
2. Suggest a safe new target such as `docs/eva_project_note.md`.
3. Generate deterministic Markdown without cloud calls.
4. Create a FileAgent approval request.
5. Require the approval's exact phrase before future apply.
6. Use sandbox apply and verification before any real create.
7. Show narrow real-create eligibility.
8. Require `confirm real create <approval_id>` for the Phase 12L gate.
9. Verify the created file by hash.
10. Offer `confirm rollback real create <approval_id>` only for unchanged Eva-created files.

Natural examples:

- `eva ask create a project note about Eva`
- `eva ask make a safe markdown note about FileAgent`
- `eva ask draft and safely create a note about this project`

Debug commands:

- `eva golden workflow status`
- `eva golden workflow start project note`
- `eva golden workflow demo`

The workflow does not bypass FileAgent path policy, approval ledger checks, sandbox-only apply boundaries, real-create eligibility, exact confirmation, verification, or rollback checks. Broad writes remain disabled.

## Phase 12K Verification UX

Phase 12K adds a fast smoke verifier and quick/full master verifier profiles around the FileAgent and Phase 12 safety surfaces:

- `scripts/verify_eva_smoke.py`
- `scripts/verify_eva_phase12_stabilization.py`
- `scripts/verify_eva_all.py --quick`
- `scripts/verify_eva_all.py --full`

Related chat/status commands:

- `eva smoke status`
- `eva verify quick command`
- `eva verify full command`
- `eva phase 12 status`
- `eva ask run quick check`

These commands show status or manual verifier commands only. They do not run shell commands from chat, do not apply FileAgent drafts, and do not grant broad write access.

## Phase 12M Specialist And Skill Workflow Foundation

Phase 12M adds role and skill workflow metadata around FileAgent without adding a new executor.

New safe surfaces:

- `eva specialists status`
- `eva specialist fileagent_workflow_specialist`
- `eva skills status`
- `eva skill fileagent_create_project_note`
- `eva workflows status`
- `eva workflow fileagent_project_note_create`

The FileAgent project-note workflow explains the safe sequence: interpret request, draft preview, approval metadata, sandbox apply/verify, Phase 12L narrow real-create gate, verification, and rollback guidance. It does not create files by itself. Broad edits, overwrites, source/config/runtime writes, browser/desktop control, terminal execution, cloud calls, and MCP remain disabled.

## Phase 12N Golden Workflow UX Polish

Phase 12N adds latest-state handling for the FileAgent project-note workflow.

New status/debug commands:

- `eva workflow state`
- `eva workflow next`
- `eva workflow latest approval`
- `eva workflow latest sandbox`
- `eva workflow latest real create`
- `eva workflow latest rollback`
- `eva file latest status`
- `eva file latest real create`
- `eva file latest rollback`

Natural requests such as `eva ask continue the project note workflow`, `eva ask what should I do next`, `eva ask verify the latest real create`, and `eva ask rollback the latest real create` now summarize the latest approval/apply context and provide a clear next step. If multiple candidates exist, Eva lists safe approval IDs and asks the user to specify one. Exact confirmation remains required for Phase 12L real create and rollback.

## Safety Notes

All normal user-facing output uses repo-relative paths and friendly summaries. Raw dicts, dataclass reprs, SQLite rows, stack traces, absolute paths, raw file dumps, and secret contents must not appear in normal FileAgent responses.

## Limitations

FileAgent understanding is intentionally shallow. It does not execute code, install packages, call cloud APIs, parse PDFs/DOCX files, perform OCR, index automatically, or prove semantic correctness. It can say what the repo appears to be from safe filenames, small key files, and bounded text previews.
