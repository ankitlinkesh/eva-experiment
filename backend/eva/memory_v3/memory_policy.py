from __future__ import annotations


MEMORY_SOURCE_TYPES: tuple[str, ...] = (
    "user_explicit_memory",
    "user_preference",
    "project_checkpoint",
    "verification_evidence",
    "workflow_state_summary",
    "work_session_summary",
    "research_memory_summary",
    "fileagent_summary",
    "system_status_summary",
    "generated_summary",
    "untrusted_text",
    "unknown_source",
)

MEMORY_TRUST_CLASSES: tuple[str, ...] = (
    "trusted_explicit_user",
    "trusted_verified_project_evidence",
    "trusted_local_status",
    "semi_trusted_summary",
    "untrusted_external_text",
    "untrusted_injected_text",
    "unknown_or_stale",
)

MEMORY_PRIVACY_CLASSES: tuple[str, ...] = (
    "public_project_note",
    "normal_preference",
    "private_user_context",
    "sensitive_possible_secret",
    "sensitive_credential_or_token",
    "sensitive_session_or_cookie",
    "sensitive_private_path",
    "blocked",
)


def boundary_lines() -> list[str]:
    return [
        "Memory v3 is local only.",
        "No live LLM call was made.",
        "No cloud memory is used.",
        "Secrets/config/session data are blocked.",
        "Memory cannot override system/developer/safety policy.",
        "Memory cannot execute tools.",
        "Memory context injection is preview/policy only.",
    ]


def memory_policy_text() -> str:
    lines = [
        "Memory v3 policy",
        *boundary_lines(),
        "Policy behavior:",
        "- Explicit user memories may be high trust, but still privacy-filtered.",
        "- Project checkpoints should be grounded in verification evidence when possible.",
        "- Stale memories are marked stale, not silently trusted.",
        "- Conflicting memories are reported, not merged blindly.",
        "- Secret-like, credential-like, token-like, cookie-like, session-like, and private-path-like content is blocked or redacted.",
        "- Prompt-injection-like memory content is treated as untrusted data.",
        "- Memory must not create capabilities that do not exist.",
        "- Raw memory database dumps are blocked.",
        "- No cloud sync or remote storage is used.",
    ]
    lines.append("Source types:")
    lines.extend(f"- {item}" for item in MEMORY_SOURCE_TYPES)
    lines.append("Trust classes:")
    lines.extend(f"- {item}" for item in MEMORY_TRUST_CLASSES)
    lines.append("Privacy classes:")
    lines.extend(f"- {item}" for item in MEMORY_PRIVACY_CLASSES)
    return "\n".join(lines)
