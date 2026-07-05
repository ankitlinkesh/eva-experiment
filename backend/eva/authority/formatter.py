from __future__ import annotations

from .models import AuthorityDecision


def format_authority_decision(decision: AuthorityDecision) -> str:
    lines = [
        "Authority decision",
        "",
        f"Action: {decision.action_type}",
        f"Category: {decision.action_category}",
        f"Mode: {decision.mode}",
        f"Risk: {decision.risk_level}",
        f"Allowed: {'yes' if decision.allowed else 'no'}",
        f"Real execution available: {'yes' if decision.real_execution_available else 'no'}",
        f"Sandbox only: {'yes' if decision.sandbox_only else 'no'}",
        f"Verification required: {'yes' if decision.verification_required else 'no'}",
        f"Rollback available: {'yes' if decision.rollback_available else 'no'}",
    ]
    if decision.capability_id:
        lines.append(f"Capability: {decision.capability_id}")
    if decision.agent_name:
        lines.append(f"Agent: {decision.agent_name}")
    if decision.approval_id:
        lines.append(f"Approval ID: {decision.approval_id}")
    lines.extend(["", "Reason:", decision.reason])
    if decision.blocked_reason:
        lines.extend(["", "Blocked:", decision.blocked_reason])
    lines.extend(["", "Scope:", "Authority output is a local decision summary. It does not execute tools by itself."])
    return "\n".join(lines)
