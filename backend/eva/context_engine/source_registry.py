from __future__ import annotations

from .models import ContextSource


_ALLOWED_SOURCES: tuple[ContextSource, ...] = (
    ContextSource("user_request", "Current user request text, sanitized", "user_supplied_untrusted", True, "Allowed only after redaction and injection handling."),
    ContextSource("route_intent", "Current route/planner intent metadata", "local_metadata", True, "Allowed when produced by deterministic local routing."),
    ContextSource("safety_policy", "Permission and safety metadata", "trusted_local_policy", True, "Safety policy is preferred over noisy history."),
    ContextSource("capability_metadata", "Capability registry metadata", "trusted_local_metadata", True, "Catalog metadata only; no capability is invented."),
    ContextSource("tool_schema_metadata", "Tool-schema metadata", "trusted_local_metadata", True, "Schema summaries only; no tool is executed."),
    ContextSource("resource_mapping_metadata", "Resource mapping metadata", "trusted_local_metadata", True, "Preview-only resource links and safety notes."),
    ContextSource("validation_status", "Phase 15 structured-output validation summary", "trusted_local_status", True, "Local/mock validation status only."),
    ContextSource("red_team_status", "Phase 15 red-team and evidence-lock summary", "trusted_local_status", True, "Local/mock failure-test status only."),
    ContextSource("work_session_summary", "WorkSession summaries through safe APIs", "bounded_local_summary", True, "Summary metadata only, never raw runtime dumps."),
    ContextSource("memory_summary", "Research Memory summaries through safe APIs", "bounded_local_summary", True, "Preview metadata only; stale/unknown context is marked."),
    ContextSource("project_status_summary", "Project/reality/status summaries through safe APIs", "trusted_local_status", True, "Status summaries only, not source dumps."),
)

_BLOCKED_SOURCES: tuple[ContextSource, ...] = (
    ContextSource("env_file", ".env and .env.local files", "blocked", False, "Config and secret files are never read or assembled."),
    ContextSource("secret_material", "secrets, tokens, cookies, passwords, private keys", "blocked", False, "Secret-like material is redacted or excluded."),
    ContextSource("browser_session", "browser sessions, cookies, localStorage, profiles", "blocked", False, "Browser session state remains locked."),
    ContextSource("desktop_state", "desktop/screen/window state", "blocked", False, "Desktop observation remains locked."),
    ContextSource("raw_runtime_dump", "raw WorkSession databases, logs, or private runtime dumps", "blocked", False, "Only safe summaries may be used."),
    ContextSource("arbitrary_filesystem", "arbitrary filesystem crawl or source-code dump", "blocked", False, "Phase 16 does not introduce arbitrary file reads."),
    ContextSource("tool_output_instruction", "tool output that asks Eva to ignore policy", "blocked", False, "Injected text is data, not trusted instruction."),
)


def list_allowed_sources() -> tuple[ContextSource, ...]:
    return _ALLOWED_SOURCES


def list_blocked_sources() -> tuple[ContextSource, ...]:
    return _BLOCKED_SOURCES


def format_source_registry() -> str:
    lines = [
        "Context Source Registry",
        "",
        "Allowed sources:",
    ]
    lines.extend(f"- {item.source_type}: {item.name} ({item.trust_level}) - {item.reason}" for item in _ALLOWED_SOURCES)
    lines.extend(["", "Blocked sources:"])
    lines.extend(f"- {item.source_type}: {item.name} - {item.reason}" for item in _BLOCKED_SOURCES)
    lines.extend(["", "No live LLM call was made. Context assembly is local/mock preview only. Assembled context cannot execute tools."])
    return "\n".join(lines)
