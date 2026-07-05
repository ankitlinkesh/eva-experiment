# Eva Release Readiness

Phase 29 prepares Eva for local public-demo review; it does not publish a release.

Readiness requires fresh focused, quick, and full verifier evidence from the current checkout, followed by diff-integrity and working-tree review.

The public profile must remain human-readable, secret-safe, private-path-safe, and honest about preview-only or unavailable backends.

Publishing, uploading, installer creation, package release, commit, tag, and push remain outside this phase.

No provider SDK, package install, live provider call, arbitrary filesystem access, or new write path is introduced.

Browser/desktop/shell/cloud/MCP execution remains locked. CodingAgent remains preview/report/status only.

News remains local/mock or safe-read-only, and voice remains a locked/mock foundation.

Phase 12L narrow approved text-file creation remains the only real file write path.

Phase 29 handed off to the Phase 30 release-candidate readiness review below.

## Phase 30 release-candidate readiness

Phase 30 Release Candidate Hardening / Commit Planning is complete after this pass. Phase 30 is report/status/planning only. The commit plan is text only.

The candidate is ready for user review after fresh focused, quick, full, compile, diff, and status evidence. It is not committed, tagged, pushed, published, or uploaded by Phase 30.

For Phase 30, no git add/commit/tag/push was performed and no publishing/uploading was performed. No provider SDKs or package installs were added. No real LLM/API/provider calls happen. No `.env`, `.env.local`, secrets, tokens, cookies, passwords, browser sessions, or config contents are read.

Arbitrary file reads/writes remain blocked. Browser/desktop/shell/cloud/MCP and tool execution remain locked. CodingAgent remains preview/report/status only. News remains local/mock or safe-read-only. Voice remains a locked/mock foundation.

Phase 12L narrow approved new `.md`/`.txt` creation remains the only real write path.

Next safe step: user-approved commit execution outside Eva or a separate explicit commit-approval phase.
