# Eva Public Capability Map

- Command system: deterministic local commands and human-readable refusals.
- Planner and agent loop: bounded planning and preview-only action models.
- Capability registry: permissions, resources, schemas, and verifier metadata.
- FileAgent: inspection and previews, plus the existing Phase 12L narrow create gate.
- Browser: public-URL read-only observation; control locked.
- Desktop: one-shot redacted observation; control locked and dry-run policy only.
- News: local/mock or safe-read-only reports; unrestricted crawling locked.
- CodingAgent: task, patch-plan, review, test-plan, risk, and handoff previews; source editing locked.
- Voice: locked/mock foundation; microphone and audio execution locked.
- Release demo: local report/status/profile only; publishing and git release actions locked.

No broad real execution, secret/config/session access, shell/cloud/MCP execution, or new write path is part of the public profile.

Phase 12L narrow approved text-file creation remains the only real file write path.

## Phase 30 release-candidate capabilities

Phase 30 Release Candidate Hardening / Commit Planning is complete after this pass. Phase 30 is report/status/planning only. The commit plan is text only.

- `rc.status`: deterministic readiness and lock status.
- `rc.manifest`: audited dirty-tree grouping snapshot.
- `rc.commit_plan`: human-readable commit candidates and checks as text only.
- `rc.hardening_report`: bounded-claim and safety findings.
- `rc.checklist`: user-reviewable release-candidate checklist.
- `rc.readiness`: safe-to-commit guidance without Git execution.
- `rc.safety_proof`: deterministic safety-boundary evidence.
- `rc.verification`: manual commands without execution.

For Phase 30, no git add/commit/tag/push was performed and no publishing/uploading was performed. No provider SDKs or package installs were added. No real LLM/API/provider calls happen. No `.env`, `.env.local`, secrets, tokens, cookies, passwords, browser sessions, or config contents are read.

Arbitrary file reads/writes and browser/desktop/shell/cloud/MCP/tool execution remain blocked. CodingAgent remains preview/report/status only. News remains local/mock or safe-read-only. Voice remains a locked/mock foundation. Phase 12L narrow approved new `.md`/`.txt` creation remains the only real write path.

Next safe step: user-approved commit execution outside Eva or a separate explicit commit-approval phase.
