from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class WorkflowCandidate:
    approval_id: str
    display_path: str
    state: str
    created_at: str
    eligible: bool = False
    required_phrase: str = ""
    reason: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class LatestWorkflowContext:
    kind: str
    status: str
    candidates: tuple[WorkflowCandidate, ...] = ()
    message: str = ""
    safe_next_action: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowNextStep:
    action: str
    title: str
    message: str
    suggested_command: str | None = None
    required_phrase: str | None = None
    candidates: tuple[WorkflowCandidate, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowStateSummary:
    pending_approval_count: int
    approved_for_future_apply_count: int
    consumed_real_create_count: int
    latest_pending: LatestWorkflowContext
    latest_approved: LatestWorkflowContext
    latest_sandbox_apply: LatestWorkflowContext
    latest_real_create: LatestWorkflowContext
    latest_rollback_available: LatestWorkflowContext
    ambiguity_status: str
    safe_next_action: str
    locked_features: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def summarize_fileagent_workflow_state() -> WorkflowStateSummary:
    from ..file_agent.approval_ledger import list_file_approval_requests

    pending = list_file_approval_requests(status="pending", limit=50)
    approved = list_file_approval_requests(status="approved_for_future_apply", limit=50)
    consumed = list_file_approval_requests(status="consumed_by_real_create", limit=50)
    latest_pending = find_latest_pending_approval()
    latest_approved = find_latest_approved_approval()
    latest_sandbox = find_latest_sandbox_apply()
    latest_real = find_latest_real_create()
    latest_rollback = find_latest_rollback_available()
    ambiguous = "yes" if any(ctx.status == "multiple" for ctx in (latest_pending, latest_approved, latest_sandbox, latest_real, latest_rollback)) else "no"
    next_step = classify_next_fileagent_step("what should I do next")
    return WorkflowStateSummary(
        pending_approval_count=len(pending),
        approved_for_future_apply_count=len(approved),
        consumed_real_create_count=len(consumed),
        latest_pending=latest_pending,
        latest_approved=latest_approved,
        latest_sandbox_apply=latest_sandbox,
        latest_real_create=latest_real,
        latest_rollback_available=latest_rollback,
        ambiguity_status=ambiguous,
        safe_next_action=next_step.message,
        locked_features=_locked_features(),
    )


def find_latest_pending_approval() -> LatestWorkflowContext:
    from ..file_agent.approval_ledger import list_file_approval_requests

    candidates = tuple(_approval_candidate(item) for item in list_file_approval_requests(status="pending", limit=20))
    return _context("pending_approval", candidates, none_message="No pending FileAgent approval is waiting.")


def find_latest_approved_approval() -> LatestWorkflowContext:
    from ..file_agent.approval_ledger import list_file_approval_requests

    candidates = tuple(_approval_candidate(item, include_eligibility=True) for item in list_file_approval_requests(status="approved_for_future_apply", limit=20))
    return _context("approved_approval", candidates, none_message="No approved FileAgent record is waiting for sandbox or real-create steps.")


def find_latest_sandbox_apply() -> LatestWorkflowContext:
    from ..file_agent.approval_ledger import list_file_approval_requests
    from ..file_agent.apply_executor import _load_latest_result

    candidates: list[WorkflowCandidate] = []
    for approval in list_file_approval_requests(limit=50):
        result = _load_latest_result(approval.approval_id)
        if result and result.ok:
            candidates.append(
                WorkflowCandidate(
                    approval_id=approval.approval_id,
                    display_path=_safe_display_path(approval.display_path),
                    state="sandbox_applied",
                    created_at=_short_time(result.created_at or approval.created_at),
                    eligible=True,
                    reason="Sandbox apply result exists and real project files were not touched.",
                )
            )
    return _context("sandbox_apply", tuple(candidates), none_message="No latest sandbox apply result is recorded.")


def find_latest_real_create() -> LatestWorkflowContext:
    from ..file_agent.approval_ledger import list_file_approval_requests

    candidates = []
    for approval in list_file_approval_requests(limit=50):
        path = str(getattr(approval, "real_apply_created_path", "") or "")
        if path:
            verified = "verified" if getattr(approval, "real_apply_verified_at", "") else "created"
            candidates.append(
                WorkflowCandidate(
                    approval_id=approval.approval_id,
                    display_path=_safe_display_path(path),
                    state=f"real_create_{verified}",
                    created_at=_short_time(getattr(approval, "real_apply_verified_at", "") or approval.created_at),
                    eligible=True,
                    reason="Narrow real create record exists.",
                )
            )
    return _context("real_create", tuple(candidates), none_message="No real create record exists yet.")


def find_latest_rollback_available() -> LatestWorkflowContext:
    from ..file_agent.approval_ledger import list_file_approval_requests

    candidates = []
    for approval in list_file_approval_requests(limit=50):
        path = str(getattr(approval, "real_apply_created_path", "") or "")
        if not path:
            continue
        if str(getattr(approval, "real_apply_rollback_status", "") or "") == "rolled_back":
            continue
        phrase = f"confirm rollback real create {approval.approval_id}"
        candidates.append(
            WorkflowCandidate(
                approval_id=approval.approval_id,
                display_path=_safe_display_path(path),
                state="rollback_available_if_unchanged",
                created_at=_short_time(approval.created_at),
                eligible=True,
                required_phrase=phrase,
                reason="Rollback can remove only an unchanged Eva-created file.",
            )
        )
    return _context("rollback", tuple(candidates), none_message="No rollback-eligible real create record exists.")


def classify_next_fileagent_step(request_text: str) -> WorkflowNextStep:
    text = " ".join(str(request_text or "").lower().split())
    if "verify" in text and "real create" in text:
        ctx = find_latest_real_create()
        if ctx.status == "single":
            candidate = ctx.candidates[0]
            return WorkflowNextStep("verify_real_create", "Verify latest real create", "One real create record was found. Verification can use the latest approval id.", f"eva file approval real verify {candidate.approval_id}", candidates=ctx.candidates)
        return WorkflowNextStep("disambiguate_real_create", "Real-create verification needs a target", ctx.message, candidates=ctx.candidates)
    if "rollback" in text and "real create" in text:
        ctx = find_latest_rollback_available()
        if ctx.status == "single":
            candidate = ctx.candidates[0]
            return WorkflowNextStep("show_rollback_phrase", "Rollback requires exact confirmation", "One rollback-eligible record was found. Do not run rollback without the exact phrase.", f"eva file approval real rollback {candidate.approval_id} confirm {candidate.required_phrase}", candidate.required_phrase, ctx.candidates)
        return WorkflowNextStep("disambiguate_rollback", "Rollback needs a target", ctx.message, candidates=ctx.candidates)
    if any(term in text for term in ("real", "approved docs note", "approved text file", "approved docs file")):
        ctx = find_latest_approved_approval()
        eligible = tuple(candidate for candidate in ctx.candidates if candidate.eligible)
        if len(eligible) == 1:
            candidate = eligible[0]
            phrase = f"confirm real create {candidate.approval_id}"
            return WorkflowNextStep("show_real_create_phrase", "Real create requires exact confirmation", "One eligible approval was found. Exact confirmation is still required before creating the file.", f"eva file approval real create {candidate.approval_id} {phrase}", phrase, eligible)
        if len(eligible) > 1:
            return WorkflowNextStep("disambiguate_approved_approval", "Multiple eligible approvals", "Multiple approved records are eligible. Specify the approval id before real create.", candidates=eligible)
        return WorkflowNextStep("missing_eligible_approval", "No eligible approved record", "No approved FileAgent record is currently eligible for the Phase 12L real-create gate.", candidates=ctx.candidates)
    approved = find_latest_approved_approval()
    if approved.status == "single":
        candidate = approved.candidates[0]
        if candidate.eligible:
            phrase = f"confirm real create {candidate.approval_id}"
            return WorkflowNextStep("show_real_create_phrase", "Approved record is ready for exact real-create confirmation", "One approved eligible record exists. You may sandbox/verify first or use the exact real-create phrase.", f"eva ask confirm real create {candidate.approval_id}", phrase, approved.candidates)
        return WorkflowNextStep("show_sandbox_next", "Approved record needs sandbox or eligibility review", candidate.reason or "Review sandbox apply and real-create eligibility before continuing.", f"eva file approval sandbox apply {candidate.approval_id}", candidates=approved.candidates)
    if approved.status == "multiple":
        return WorkflowNextStep("disambiguate_approved_approval", "Multiple approved records", approved.message, candidates=approved.candidates)
    pending = find_latest_pending_approval()
    if pending.status == "single":
        candidate = pending.candidates[0]
        return WorkflowNextStep("approve_pending", "Approval is needed", "One pending approval exists. Review it and approve with its exact phrase before any sandbox or real-create step.", f"eva file approval {candidate.approval_id}", candidates=pending.candidates)
    if pending.status == "multiple":
        return WorkflowNextStep("disambiguate_pending_approval", "Multiple pending approvals", pending.message, candidates=pending.candidates)
    return WorkflowNextStep("start_project_note", "Start with a draft and approval", "No active project-note approval exists. Draft the note and create a FileAgent approval request first.", "eva ask create a project note about the phase")


def format_workflow_state_summary(summary: WorkflowStateSummary | None = None) -> str:
    summary = summary or summarize_fileagent_workflow_state()
    lines = [
        "FileAgent workflow state",
        "",
        f"Pending approvals: {summary.pending_approval_count}",
        f"Approved for future apply: {summary.approved_for_future_apply_count}",
        f"Real-create records: {summary.consumed_real_create_count}",
        f"Ambiguity: {summary.ambiguity_status}",
        "",
        "Latest approval:",
        _context_line(summary.latest_pending),
        _context_line(summary.latest_approved),
        "",
        "Latest apply state:",
        _context_line(summary.latest_sandbox_apply),
        _context_line(summary.latest_real_create),
        _context_line(summary.latest_rollback_available),
        "",
        "Safe next action:",
        summary.safe_next_action,
        "",
        "Locked features:",
    ]
    lines.extend(f"- {item}" for item in summary.locked_features)
    lines.append("Scope: status only. No workflow step was executed.")
    return "\n".join(lines)


def format_workflow_next_step(next_step: WorkflowNextStep | None = None) -> str:
    item = next_step or classify_next_fileagent_step("what should I do next")
    lines = ["Workflow next step", "", f"Action: {item.action}", f"Title: {item.title}", "Safe next step:", item.message]
    if item.required_phrase:
        lines.extend(["", "Required exact phrase:", item.required_phrase])
    if item.suggested_command:
        lines.extend(["", "Suggested command:", item.suggested_command])
    if item.candidates:
        lines.extend(["", "Candidates:"])
        lines.extend(_candidate_line(candidate) for candidate in item.candidates[:10])
    lines.extend(["", "Scope: next-step guidance only. No file was created, modified, deleted, moved, copied, or renamed. No browser, desktop, shell, MCP, or cloud action was executed."])
    return "\n".join(lines)


def format_latest_workflow_context(context: LatestWorkflowContext) -> str:
    lines = [f"Latest {context.kind.replace('_', ' ')}", "", f"Status: {context.status}", context.message]
    if context.candidates:
        lines.extend(["", "Candidates:"])
        lines.extend(_candidate_line(candidate) for candidate in context.candidates[:10])
    if context.safe_next_action:
        lines.extend(["", "Safe next action:", context.safe_next_action])
    lines.extend(["", "Scope: latest-state lookup only. Nothing was executed."])
    return "\n".join(lines)


def _context(kind: str, candidates: tuple[WorkflowCandidate, ...], *, none_message: str) -> LatestWorkflowContext:
    if not candidates:
        return LatestWorkflowContext(kind=kind, status="none", candidates=(), message=none_message, safe_next_action="Create or inspect a FileAgent approval before continuing.")
    if len(candidates) == 1:
        candidate = candidates[0]
        return LatestWorkflowContext(kind=kind, status="single", candidates=candidates, message=f"One likely {kind.replace('_', ' ')} candidate: {candidate.approval_id} -> {candidate.display_path}.", safe_next_action=candidate.reason or "Continue with the exact candidate id.")
    return LatestWorkflowContext(kind=kind, status="multiple", candidates=candidates, message=f"Multiple {kind.replace('_', ' ')} candidates exist. Specify an approval id; Eva will not guess.", safe_next_action="Specify the approval id you want to continue.")


def _approval_candidate(approval: object, *, include_eligibility: bool = False) -> WorkflowCandidate:
    eligible = False
    phrase = ""
    reason = str(getattr(approval, "safety_summary", "") or "Approval metadata exists.")
    if include_eligibility:
        try:
            from ..file_agent.real_apply import evaluate_real_apply_eligibility

            eligibility = evaluate_real_apply_eligibility(getattr(approval, "approval_id", ""))
            eligible = bool(eligibility.allowed)
            phrase = f"confirm real create {approval.approval_id}" if eligible else ""
            reason = eligibility.reason
        except Exception:
            reason = "Eligibility could not be checked safely."
    return WorkflowCandidate(
        approval_id=str(getattr(approval, "approval_id", "")),
        display_path=_safe_display_path(getattr(approval, "display_path", "")),
        state=str(getattr(approval, "status", "unknown")),
        created_at=_short_time(getattr(approval, "created_at", "")),
        eligible=eligible,
        required_phrase=phrase,
        reason=reason,
    )


def _candidate_line(candidate: WorkflowCandidate) -> str:
    eligibility = "eligible" if candidate.eligible else "not eligible"
    time = f"; {candidate.created_at}" if candidate.created_at else ""
    return f"- {candidate.approval_id}: {candidate.display_path}; {candidate.state}; {eligibility}{time}"


def _context_line(context: LatestWorkflowContext) -> str:
    if context.status == "single" and context.candidates:
        candidate = context.candidates[0]
        return f"- {context.kind}: {candidate.approval_id} -> {candidate.display_path}; {candidate.state}"
    return f"- {context.kind}: {context.message}"


def _safe_display_path(path: object) -> str:
    text = str(path or "unknown").strip().replace("\\", "/")
    if not text:
        return "unknown"
    if ":" in text or text.startswith("/") or ".env" in text.lower():
        return "safe target"
    parts = [part for part in text.split("/") if part and part not in {".", ".."}]
    return "/".join(parts[:3]) if parts else "safe target"


def _short_time(value: object) -> str:
    text = str(value or "").strip()
    if "T" in text:
        return text.split("+", 1)[0].replace("T", " ")[:19]
    return text[:19]


def _locked_features() -> tuple[str, ...]:
    return (
        "existing file editing: locked",
        "source-code editing: locked",
        "overwrite/append/replace: locked",
        "browser control: locked",
        "desktop control: locked",
        "shell execution: locked",
        "MCP execution: locked",
        "news dashboard: planned later",
        "CodingAgent real edits: planned/read-only future",
    )
