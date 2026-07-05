from __future__ import annotations

from .models import GateEvaluation


def format_gate_evaluation(evaluation: GateEvaluation) -> str:
    lines = [
        "Controlled Execution Gates evaluation",
        evaluation.no_live_llm_call_statement,
        "Execution gates are local/mock policy preview only.",
        evaluation.no_tool_execution_statement,
        "Approval alone does not execute.",
        "Confirmation alone does not execute unless an existing implemented gate accepts it.",
        "Browser/desktop/shell/cloud/MCP/package execution remains locked.",
        "Secrets/config/session data are blocked.",
        evaluation.no_new_write_path_statement,
        "Evaluation:",
        f"- Gate evaluation ID: {evaluation.gate_evaluation_id}",
        f"- Request summary: {evaluation.request_summary}",
        f"- Requested action class: {evaluation.requested_action_class}",
        f"- Requested capability: {evaluation.requested_capability}",
        f"- Permission class: {evaluation.permission_class}",
        f"- Risk level: {evaluation.risk_level}",
        f"- Decision state: {evaluation.decision_state}",
        f"- Approval requirement: {evaluation.approval_requirement}",
        f"- Confirmation requirement: {evaluation.confirmation_requirement}",
        f"- Rollback availability: {evaluation.rollback_availability}",
        f"- Audit requirement: {evaluation.audit_requirement}",
        f"- Blocked reason: {evaluation.blocked_reason or 'none'}",
        f"- Eligible existing gate: {evaluation.eligible_existing_gate or 'none'}",
        f"- Future gate requirement: {evaluation.future_gate_requirement or 'none'}",
        f"- Final readiness status: {evaluation.final_readiness_status}",
        "Safety notes:",
    ]
    lines.extend(f"- {item}" for item in evaluation.safety_notes)
    return "\n".join(lines)
