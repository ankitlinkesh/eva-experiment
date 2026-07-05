from __future__ import annotations

from .approval_requirements import approval_policy_text
from .audit_policy import audit_policy_text
from .confirmation_policy import confirmation_policy_text
from .gate_evaluator import evaluate_execution_gate
from .gate_policy import ACTION_CLASSES, BLOCKED_ACTION_CLASSES, DECISION_STATES, boundary_lines, gate_policy_text
from .rollback_policy import rollback_policy_text
from .status import get_execution_gates_status


def format_execution_gate_status() -> str:
    status = get_execution_gates_status()
    return "\n".join(
        [
            "Controlled Execution Gates status",
            *boundary_lines(),
            f"Status: {status.status}.",
            f"Mode: {status.mode}.",
            f"Provider SDKs enabled: {status.provider_sdks_enabled}.",
            f"Arbitrary file reads enabled: {status.arbitrary_file_reads_enabled}.",
            f"Arbitrary file writes enabled: {status.arbitrary_file_writes_enabled}.",
            f"New write paths enabled: {status.new_write_paths_enabled}.",
            f"Existing real write boundary: {status.existing_real_write_boundary}.",
            f"Next phase: {status.next_phase}.",
        ]
    )


def format_execution_gate_policy() -> str:
    return gate_policy_text()


def format_execution_gate_evaluation(request: str = "show execution gates status") -> str:
    return evaluate_execution_gate(request).format()


def format_execution_gate_approvals() -> str:
    return approval_policy_text()


def format_execution_gate_confirmations() -> str:
    return confirmation_policy_text()


def format_execution_gate_rollback() -> str:
    return "\n".join([rollback_policy_text(), "", audit_policy_text()])


def format_execution_gate_blocked_actions() -> str:
    lines = [
        "Controlled Execution Gates blocked actions",
        *boundary_lines(),
        "Blocked action classes:",
    ]
    lines.extend(f"- {item}" for item in sorted(BLOCKED_ACTION_CLASSES))
    lines.extend(
        [
            "- forbidden_secret_access",
            "- forbidden_credential_access",
            "- forbidden_raw_runtime_dump",
            "- unknown_or_hallucinated_action",
            "Future gate candidates are reported locked, not executable.",
        ]
    )
    return "\n".join(lines)


def format_execution_gate_readiness() -> str:
    lines = [
        "Controlled Execution Gates readiness",
        *boundary_lines(),
        "Ready for deterministic local gate policy/status/evaluation reports.",
        "No provider SDKs are used.",
        "No .env, .env.local, secrets, tokens, cookies, passwords, browser sessions, or config secrets are read.",
        "Arbitrary file reads/writes are blocked.",
        "Future gates are described but locked.",
        "Decision states available:",
    ]
    lines.extend(f"- {item}" for item in DECISION_STATES)
    lines.append("Action classes available:")
    lines.extend(f"- {item}" for item in ACTION_CLASSES)
    lines.append("Next phase: Phase 21 Memory v3.")
    return "\n".join(lines)
