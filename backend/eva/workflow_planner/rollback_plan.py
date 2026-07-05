from __future__ import annotations

from .models import WorkflowRollbackPlan


def build_rollback_plan() -> WorkflowRollbackPlan:
    return WorkflowRollbackPlan(
        status="preview_only",
        steps=(
            "Record planned workflow steps as metadata only.",
            "If future execution gates exist, require explicit checkpoint and approval before action.",
            "Phase 12L rollback remains limited to unchanged Eva-created .md/.txt files only.",
        ),
    )
