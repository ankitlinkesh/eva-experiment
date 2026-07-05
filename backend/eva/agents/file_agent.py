from __future__ import annotations

from typing import Any

from ..schemas.results import EvaAgentResult
from .base import EvaAgent
from .contracts import EvaAgentResponse, request_from_any


class FileAgent(EvaAgent):
    def __init__(self) -> None:
        super().__init__(
            name="file",
            description="Routes safe repo-scoped file inspection, filename search, text preview, heuristic understanding, project inventory, draft/diff previews, apply-readiness planning, approval-ledger metadata, and sandbox-only apply harness checks to FileAgent v1.",
            capabilities=("file", "folder", "project structure", "project inventory", "project explain", "inspect file", "preview text", "summarize file", "understand file", "search files", "draft preview", "diff preview", "apply readiness", "rollback plan", "approval ledger", "deferred apply queue", "sandbox apply harness"),
            delegated_core="FileAgent v1 read-only foundation",
        )

    def can_handle(self, intent: str, state: Any | None = None) -> float:
        text = str(intent or "").lower()
        if any(marker in text for marker in ("sandbox apply", "test this approved file change", "verify sandbox apply", "rollback sandbox apply")):
            return 0.96
        if any(marker in text for marker in ("approve this file change", "create an approval", "approval request", "approvals pending", "pending approvals", "is this file edit approved", "apply approved file change", "approve readme edit")):
            return 0.95
        if any(marker in text for marker in ("apply this change", "apply this file change", "is this file edit safe", "file change safe", "prepare to update", "update readme", "write this to file", "edit this file")):
            return 0.94
        if any(marker in text for marker in ("draft readme", "draft report", "make a report", "create report", "append to readme", "replace text", "diff preview", "draft file", "create changelog")):
            return 0.93
        if any(marker in text for marker in ("what is this project", "explain this repo", "project inventory", "project explain", "missing files", "key files", "dependencies", "inspect file", "read file", "preview file", "file preview", "folder inspect", "project structure", "find file", "search file", "file search", "summarize readme", "summarise readme")):
            return 0.92
        if any(marker in text for marker in ("file", "folder", "readme", ".md", ".py", ".json")) and not any(marker in text for marker in ("delete", "move", "rename")):
            return 0.72
        return 0.04

    def plan(self, state: Any) -> EvaAgentResult:
        text = str(getattr(state, "normalized_intent", "") or getattr(state, "user_request", "")).lower()
        action_type = "file.inspect_path"
        summary = "Would inspect file or folder metadata through FileAgent v1 path policy."
        if any(marker in text for marker in ("verify sandbox apply", "sandbox verify")):
            action_type = "file.sandbox_verify_apply"
            summary = "Would verify a prior sandbox apply result only; no real file read or apply."
        elif any(marker in text for marker in ("rollback sandbox apply", "sandbox rollback")):
            action_type = "file.sandbox_rollback_apply"
            summary = "Would roll back sandbox state only; no real project file is restored."
        elif any(marker in text for marker in ("sandbox apply", "test this approved file change", "apply approved file change")):
            action_type = "file.sandbox_apply_approved"
            summary = "Would apply approved metadata inside the FileAgent sandbox harness only; real apply remains unavailable."
        elif any(marker in text for marker in ("approve this file change", "create an approval", "approval request", "approve readme edit")):
            action_type = "file.approval_request_create"
            summary = "Would create or inspect FileAgent approval metadata for a future apply; no file write or apply."
        elif any(marker in text for marker in ("approvals pending", "pending approvals", "is this file edit approved")):
            action_type = "file.approval_list_pending"
            summary = "Would list or inspect FileAgent approval metadata only; no file write or apply."
        elif any(marker in text for marker in ("apply this change", "apply this file change", "is this file edit safe", "file change safe", "prepare to update", "update readme", "write this to file", "edit this file")):
            action_type = "file.apply_readiness"
            summary = "Would evaluate future apply readiness, confirmation, backup, rollback, and verification needs; no file write."
        elif any(marker in text for marker in ("draft readme", "readme section")):
            action_type = "file.draft_readme_section"
            summary = "Would generate a README section draft in chat output only; no file write."
        elif any(marker in text for marker in ("make a report", "create report", "draft report", "report outline")):
            action_type = "file.draft_report_outline"
            summary = "Would generate a report outline draft in chat output only; no file write."
        elif any(marker in text for marker in ("append", "add this to")):
            action_type = "file.draft_append_preview"
            summary = "Would generate an append preview/diff only; no file write."
        elif "replace text" in text or "replace" in text:
            action_type = "file.draft_replace_preview"
            summary = "Would generate a replacement preview/diff only; no file write."
        elif any(marker in text for marker in ("draft file", "make a file", "create file", "write file")):
            action_type = "file.draft_create_preview"
            summary = "Would generate proposed file content in chat output only; no file creation."
        elif any(marker in text for marker in ("project summary", "write a project summary")):
            action_type = "file.draft_project_summary"
            summary = "Would draft a project summary from read-only inventory; no file write."
        elif "project todo" in text:
            action_type = "file.draft_project_todo"
            summary = "Would draft project TODO recommendations from read-only inventory; no file write."
        elif any(marker in text for marker in ("search", "find file", "filename")):
            action_type = "file.search_name"
            summary = "Would search filenames only inside the allowed project scope."
        elif any(marker in text for marker in ("understand", "summarize", "summarise", "readme")):
            action_type = "file.understand_text"
            summary = "Would summarize a safe text/code/docs file with deterministic local heuristics."
        elif any(marker in text for marker in ("preview", "read file")):
            action_type = "file.preview_text"
            summary = "Would preview a safe text/code/docs file with size limits."
        elif "folder" in text or "list" in text:
            action_type = "file.list_folder"
            summary = "Would list limited folder entries while skipping runtime and sensitive paths."
        elif any(marker in text for marker in ("missing", "checklist")):
            action_type = "file.project_missing"
            summary = "Would show a read-only missing recommended files checklist."
        elif any(marker in text for marker in ("dependencies", "dependency", "config")):
            action_type = "file.project_dependencies"
            summary = "Would detect dependency/config files from a read-only project inventory."
        elif any(marker in text for marker in ("what is this project", "explain this repo", "project explain")):
            action_type = "file.project_explain"
            summary = "Would explain the project from a bounded read-only inventory."
        elif any(marker in text for marker in ("project inventory", "project structure", "structure")):
            action_type = "file.project_inventory"
            summary = "Would build a bounded read-only project inventory."
        if any(marker in text for marker in ("delete", "move", "rename", "chmod", "copy")):
            action_type = "file.refuse_write"
            summary = "Would refuse file write/edit/delete/move actions in FileAgent v1."
        return EvaAgentResult(
            agent_name=self.name,
            ok=True,
            message="FileAgent selected for read-only file/project preview.",
            proposed_actions=[
                {
                    "agent": self.name,
                    "action_type": action_type,
                    "summary": summary,
                    "requires_permission": False,
                    "side_effect_level": "preview_only" if "draft" in action_type or "diff" in action_type else "read_only",
                    "delegate_to": self.delegated_core,
                }
            ],
            delegated_to=self.delegated_core,
        )

    def execute(self, request: Any) -> EvaAgentResponse:
        agent_request = request_from_any(request)
        text = f"{agent_request.capability_id or ''} {agent_request.input_summary}".lower()
        if any(marker in text for marker in ("write", "edit", "delete", "move", "rename", "copy", "file.delete")):
            summary = "FileAgent v1 refused this request because writes, edits, deletes, moves, renames, and copies are not enabled."
        else:
            summary = "FileAgent v1 execution is limited to explicit fast commands in this phase; planner execution is refused."
        return EvaAgentResponse(
            agent_name=type(self).__name__,
            request_id=agent_request.request_id,
            task_step_id=agent_request.task_step_id,
            action="file.execute",
            status="refused",
            summary=summary,
            details={"execution_enabled": False, "read_only_commands_only": True},
            required_permission=None,
            risk_level="medium",
            capability_id=agent_request.capability_id,
            resource_id=agent_request.resource_id,
            next_action="Use explicit commands like `eva file understand <path>`, `eva project inventory`, or `eva file draft diff <path> text <content>`.",
        )

    def explain(self) -> str:
        return "\n".join(
            [
                "FileAgent",
                "",
                self.description,
                "",
                f"Capabilities: {', '.join(self.capabilities)}",
                f"Delegates to: {self.delegated_core}",
                "Execution: explicit read-only, draft-preview, apply-readiness, approval-ledger, and sandbox-apply harness fast commands only; planner task execution is refused.",
                "",
                "Allowed: safe metadata inspection, filename search, text previews, heuristic file understanding, project inventory, project explanation, draft previews, diff previews, apply-readiness planning, approval metadata records, and sandbox-only apply tests.",
                "Draft/apply-readiness/approval mode: output or metadata only. Sandbox apply mode writes only ignored runtime sandbox files.",
                "Approval does not equal execution; approved records only mark future apply eligibility.",
                "Sandbox apply can test apply, backup, verification, and rollback lifecycle without touching real project files.",
                "Future real apply would require confirmation, backup/checkpoint, diff review, verification, and rollback planning.",
                "Refused: real writes, edits, deletes, moves, renames, copies, secrets, runtime databases, whole-drive scans, shell, MCP, Playwright, and PyAutoGUI are not enabled.",
            ]
        )
