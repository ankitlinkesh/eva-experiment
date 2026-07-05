from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesktopApprovalAuditRecord:
    record_id: str
    request: str
    state: str
    approval_level: str
    created_at: str
    note: str


@dataclass(frozen=True)
class DesktopApprovalAuditStatus:
    status: str
    records_count: int
    schema_fields: tuple[str, ...]
    storage_enabled: bool
    summary: str


def get_desktop_approval_audit_status() -> DesktopApprovalAuditStatus:
    return DesktopApprovalAuditStatus(
        status="schema/status only",
        records_count=0,
        schema_fields=("record_id", "request", "state", "approval_level", "created_at", "note"),
        storage_enabled=False,
        summary="Desktop approval audit is a schema/status preview only; no approval records are created and no execution is unlocked.",
    )
