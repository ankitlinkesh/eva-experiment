from __future__ import annotations

from .inspector import FileInspection, FolderInspection, ProjectStructure, TextPreview
from .draft_preview import DraftPreview, DraftValidationResult
from .draft_preview import format_draft_preview as _format_draft_preview
from .draft_preview import format_draft_validation as _format_draft_validation
from .write_safety import (
    RollbackPlan,
    VerificationPlan,
    WriteEligibilityDecision,
    WriteSafetyPlan,
    format_apply_readiness_report as _format_apply_readiness_report,
    format_rollback_plan as _format_rollback_plan,
    format_verification_plan as _format_verification_plan,
    format_write_eligibility as _format_write_eligibility,
    format_write_policy as _format_write_policy,
    format_write_safety_plan as _format_write_safety_plan,
)
from .approval_ledger import (
    FileApprovalRequest,
    format_file_approval_events as _format_file_approval_events,
    format_file_approval_ledger_status as _format_file_approval_ledger_status,
    format_file_approval_list as _format_file_approval_list,
    format_file_approval_request as _format_file_approval_request,
)
from .apply_executor import (
    FileApplyRequest,
    FileApplyResult,
    FileRollbackResult,
    FileVerificationResult,
    format_apply_executor_status as _format_apply_executor_status,
    format_apply_request as _format_apply_request,
    format_apply_result as _format_apply_result,
    format_rollback_result as _format_sandbox_rollback_result,
    format_verification_result as _format_sandbox_verification_result,
)
from .authority import FileAuthorityDecision, format_file_authority_decision as _format_file_authority_decision
from .project_inventory import (
    ProjectInventory,
    explain_project_inventory,
    format_key_files,
    format_missing_files,
    format_project_dependencies as _format_project_dependencies,
    format_project_inventory as _format_project_inventory,
)
from .search import FileSearchResults
from .understanding import FileUnderstanding, format_file_understanding as _format_file_understanding


def format_file_agent_status() -> str:
    from .status import format_file_agent_status as _format

    return _format()


def format_draft_preview(result: DraftPreview) -> str:
    return _format_draft_preview(result)


def format_draft_validation(result: DraftValidationResult) -> str:
    return _format_draft_validation(result)


def format_apply_readiness_report(result: DraftPreview) -> str:
    return _format_apply_readiness_report(result)


def format_write_eligibility(result: WriteEligibilityDecision) -> str:
    return _format_write_eligibility(result)


def format_write_safety_plan(result: WriteSafetyPlan) -> str:
    return _format_write_safety_plan(result)


def format_rollback_plan(result: RollbackPlan) -> str:
    return _format_rollback_plan(result)


def format_verification_plan(result: VerificationPlan) -> str:
    return _format_verification_plan(result)


def format_write_policy(path_text: str | None = None) -> str:
    return _format_write_policy(path_text)


def format_file_approval_request(result: FileApprovalRequest | None) -> str:
    return _format_file_approval_request(result)


def format_file_approval_list(results: list[FileApprovalRequest]) -> str:
    return _format_file_approval_list(results)


def format_file_approval_status() -> str:
    return _format_file_approval_ledger_status()


def format_file_approval_events(approval_id: str) -> str:
    return _format_file_approval_events(approval_id)


def format_file_authority_decision(result: FileAuthorityDecision) -> str:
    return _format_file_authority_decision(result)


def format_apply_executor_status() -> str:
    return _format_apply_executor_status()


def format_apply_request(result: FileApplyRequest) -> str:
    return _format_apply_request(result)


def format_apply_result(result: FileApplyResult) -> str:
    return _format_apply_result(result)


def format_sandbox_verification_result(result: FileVerificationResult) -> str:
    return _format_sandbox_verification_result(result)


def format_sandbox_rollback_result(result: FileRollbackResult) -> str:
    return _format_sandbox_rollback_result(result)


def format_path_inspection(result: FileInspection | FolderInspection) -> str:
    decision = result.decision
    status = "allowed" if decision.allowed else "refused"
    lines = [
        "Path inspection",
        "",
        f"Path: {decision.display_path}",
        f"Status: {status}.",
        f"Reason: {decision.reason}",
        f"Exists: {'yes' if decision.exists else 'no'}.",
        f"Type: {'folder' if decision.is_dir else 'file' if decision.is_file else 'unknown'}.",
        f"Risk: {decision.risk_level}.",
    ]
    if isinstance(result, FileInspection) and result.size_bytes is not None:
        lines.append(f"Size: {result.size_bytes} bytes.")
        if result.suffix:
            lines.append(f"Extension: {result.suffix}.")
    if decision.blocked_patterns:
        lines.append(f"Blocked by: {', '.join(decision.blocked_patterns[:4])}.")
    return "\n".join(lines)


def format_folder_inspection(result: FolderInspection) -> str:
    if not result.decision.allowed:
        return format_path_inspection(result)
    lines = [
        "Folder inspection",
        "",
        f"Path: {result.decision.display_path}",
        f"Entries shown: {len(result.entries)}.",
    ]
    for entry in result.entries[:100]:
        suffix = "/" if entry.kind == "folder" else ""
        size = f" ({entry.size_bytes} bytes)" if entry.size_bytes is not None else ""
        lines.append(f"- {entry.display_path}{suffix}{size}")
    if result.truncated:
        lines.append("Listing truncated by FileAgent v1 limits.")
    if result.skipped_count:
        lines.append(f"Skipped {result.skipped_count} sensitive/runtime entry(s).")
    return "\n".join(lines)


def format_text_preview(result: TextPreview) -> str:
    if not result.ok:
        return "\n".join(["Text preview", "", f"Path: {result.decision.display_path}", "Status: refused.", f"Reason: {result.reason}"])
    lines = [
        "Text preview",
        "",
        f"Path: {result.decision.display_path}",
        f"Size: {result.size_bytes or 0} bytes.",
    ]
    if result.truncated:
        lines.append("Preview truncated by FileAgent v1 size limits.")
    lines.extend(["", result.text])
    return "\n".join(lines)


def format_file_understanding(result: FileUnderstanding) -> str:
    return _format_file_understanding(result)


def format_project_explanation(result: ProjectInventory) -> str:
    return explain_project_inventory(result)


def format_project_inventory_report(result: ProjectInventory) -> str:
    return _format_project_inventory(result)


def format_project_missing(result: ProjectInventory) -> str:
    return format_missing_files(result)


def format_project_dependencies(result: ProjectInventory) -> str:
    return _format_project_dependencies(result)


def format_project_key_files(result: ProjectInventory) -> str:
    return format_key_files(result)


def format_file_search_results(results: FileSearchResults) -> str:
    if results.refused_reason:
        return "\n".join(["File search results", "", f"Query: {results.query or 'none'}", "Status: refused.", f"Reason: {results.refused_reason}"])
    lines = ["File search results", "", f"Query: {results.query}", f"Root: {results.root_display}", f"Matches: {len(results.results)}"]
    if not results.results:
        lines.append("No matching filenames found in the allowed project scope.")
    for item in results.results:
        suffix = "/" if item.kind == "folder" else ""
        lines.append(f"- {item.display_path}{suffix}")
    if results.truncated:
        lines.append("Results truncated by FileAgent v1 limits.")
    return "\n".join(lines)


def format_project_structure(result: ProjectStructure) -> str:
    if not result.decision.allowed:
        return "\n".join(["Project structure", "", f"Path: {result.decision.display_path}", "Status: refused.", f"Reason: {result.summary or result.decision.reason}"])
    lines = ["Project structure", "", f"Root: {result.decision.display_path}", result.summary, ""]
    lines.extend(result.lines[:120] or ["No visible project entries found."])
    if result.truncated:
        lines.append("Structure preview truncated by FileAgent v1 limits.")
    if result.skipped_count:
        lines.append(f"Skipped {result.skipped_count} sensitive/runtime entry(s).")
    return "\n".join(lines)
