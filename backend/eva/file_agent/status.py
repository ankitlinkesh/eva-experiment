from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FileAgentStatus:
    name: str = "FileAgent v1"
    read_only: bool = True
    repo_scoped: bool = True
    writes_enabled: bool = False
    heuristic_understanding: bool = True
    project_inventory: bool = True
    draft_previews: bool = True
    apply_readiness: bool = True
    approval_ledger: bool = True
    sandbox_apply_harness: bool = True
    narrow_real_create_new_text_file: bool = True
    background_watching: bool = False
    ocr_pdf_docx_parsing: bool = False


def file_agent_status() -> FileAgentStatus:
    return FileAgentStatus()


def format_file_agent_status() -> str:
    return "\n".join(
        [
            "FileAgent v1 status",
            "",
            "Mode: read-only.",
            "Scope: repo/project-scoped by default.",
            "Allowed: metadata inspection, limited folder listings, filename search, safe text previews, read-only file understanding, project inventory, and project structure previews.",
            "Understanding: deterministic local heuristics only; no cloud or LLM summaries.",
            "Draft mode: draft previews and diff previews are available in chat output only; drafts are not written to disk.",
            "Apply-readiness: planning reports can describe future confirmation, backup/checkpoint, diff review, verification, and rollback needs.",
            "Approval ledger: deferred apply approval records can be stored as local metadata only.",
            "Sandbox apply harness: approved metadata can be tested only inside ignored FileAgent runtime sandbox storage.",
            "Real apply: Phase 12L create-new-text-file only. Eva can create a brand-new .md/.txt file directly under docs/ or samples/ only after approval and exact confirmation.",
            "No real writes are available beyond that narrow create-new-text-file gate.",
            "Still blocked: existing file edits, overwrites, source code edits, config/runtime writes, broad delete, move, rename, copy, and arbitrary apply.",
            "Rollback: limited to deleting only the unchanged file Eva created through the Phase 12L record.",
            "Refused: writes, edits, deletes, moves, secrets, .env.local, browser profiles, cookies, tokens, private keys, runtime databases, whole-drive scans.",
            "Background watching: off.",
            "OCR/PDF/DOCX parsing: not available in this phase.",
            "Planner execution: dry-run/status only; no planner task is executed.",
        ]
    )
