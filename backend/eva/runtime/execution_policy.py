from __future__ import annotations

import re
from typing import Any

from ..browser.web_apps import resolve_web_app
from ..resources.registry import evaluate_resource_by_id
from ..schemas.permissions import EvaPermissionDecision
from .state import EvaRuntimeState


STATUS_COMMANDS = {
    "eva v2 status",
    "agents status",
    "guardrails status",
    "vector memory status",
    "traces status",
    "resources status",
    "resource registry status",
    "mcp status",
    "mcp policy status",
    "open source tools status",
    "open-source tools status",
}

PUBLIC_BROWSER_APP_NAMES = {
    "chatgpt",
    "github",
    "youtube",
    "gmail",
    "hugging face",
    "openrouter",
    "nvidia build",
}

CODE_READONLY_ACTIONS = {
    "code.status",
    "code.inspect_structure",
    "code.summarize_workspace",
    "code.summarize_file",
    "code.search_files",
    "code.find_symbols",
    "code.read_allowed_source_summary",
}
CODE_REFUSED_ACTIONS = {
    "code.edit_file",
    "code.delete_file",
    "code.write_file",
    "code.rename_file",
    "code.move_file",
    "code.run_shell",
    "code.run_script",
    "code.install_package",
    "code.git_commit",
    "code.git_push",
    "code.git_merge",
    "code.read_secret_file",
    "code.read_env",
}
RESEARCH_READONLY_ACTIONS = {
    "research.public_search",
    "research.public_summary",
    "research.status",
    "research.safe_lookup",
    "research.memory_status",
    "research.memory_search",
    "research.memory_topic_summary",
    "research.memory_save",
}
RESEARCH_REFUSED_ACTIONS = {
    "research.private_account_read",
    "research.logged_in_page_read",
    "research.scrape_private_page",
    "research.bypass_login",
    "research.download_private_files",
    "research.use_hidden_credentials",
}
MEMORY_READONLY_ACTIONS = {
    "memory.status",
    "memory.recall",
    "memory.search",
    "memory.read_user_approved_facts",
}
MEMORY_REFUSED_ACTIONS = {
    "memory.delete",
    "memory.dump_database",
    "memory.expose_sensitive_private_info",
}

_EXECUTE_PREFIXES = ("eva v2 execute ", "eva v2 run ")


def is_v2_execution_command(command_text: str) -> bool:
    text = " ".join(str(command_text or "").strip().lower().split())
    return any(text.startswith(prefix) for prefix in _EXECUTE_PREFIXES)


def normalize_v2_execute_request(command_text: str) -> str:
    original = str(command_text or "").strip()
    normalized = " ".join(original.lower().split())
    for prefix in _EXECUTE_PREFIXES:
        if normalized.startswith(prefix):
            return original[len(prefix) :].strip()
    return original


def evaluate_v2_execution_allowed(state: EvaRuntimeState) -> EvaPermissionDecision:
    reason = get_execution_refusal_reason(state)
    if reason:
        return EvaPermissionDecision(decision="hard_block", reason=reason)
    if is_low_risk_status_action(state):
        return EvaPermissionDecision(decision="allow", reason="Allowed low-risk read-only status action.")
    if is_allowlisted_browser_open_action(state):
        decision = evaluate_resource_by_id("eva-chrome-execution-skills")
        if decision.status not in {"allowed", "allowed_with_permission"} or decision.risk_level in {"high", "critical"}:
            return EvaPermissionDecision(decision="hard_block", reason=f"Chrome execution resource is not available: {decision.reason}")
        return EvaPermissionDecision(decision="allow", reason="Allowed low-risk public browser-open action through existing Chrome skills.")
    if is_v2_readonly_action(state):
        return EvaPermissionDecision(decision="allow", reason=_readonly_reason(state))
    return EvaPermissionDecision(decision="hard_block", reason=get_execution_refusal_reason(state) or _phase_refusal())


def is_low_risk_status_action(state: EvaRuntimeState) -> bool:
    text = _intent(state)
    if text in STATUS_COMMANDS:
        return True
    return bool(re.match(r"^resource detail [a-z0-9_.:-]+$", text) or re.match(r"^tool resource detail [a-z0-9_.:-]+$", text))


def is_allowlisted_browser_open_action(state: EvaRuntimeState) -> bool:
    return _browser_app_key(state) in PUBLIC_BROWSER_APP_NAMES


def is_allowlisted_code_readonly_action(state: EvaRuntimeState) -> bool:
    if state.selected_agent != "code":
        return False
    if not _resource_executable("eva-code-index") and not _resource_executable("eva-code-intelligence") and not _resource_executable("eva-workspace-skills"):
        return False
    return bool(_action_types(state) & CODE_READONLY_ACTIONS)


def is_allowlisted_research_readonly_action(state: EvaRuntimeState) -> bool:
    if state.selected_agent != "research":
        return False
    if not _resource_executable("eva-research-memory-v2") and not _resource_executable("eva-research-sqlite") and not _resource_executable("tavily-existing"):
        return False
    return bool(_action_types(state) & RESEARCH_READONLY_ACTIONS)


def is_allowlisted_memory_readonly_action(state: EvaRuntimeState) -> bool:
    if state.selected_agent != "memory":
        return False
    if not _resource_executable("eva-memory-sqlite"):
        return False
    return bool(_action_types(state) & MEMORY_READONLY_ACTIONS)


def is_v2_readonly_action(state: EvaRuntimeState) -> bool:
    if _action_types(state) & (CODE_REFUSED_ACTIONS | RESEARCH_REFUSED_ACTIONS | MEMORY_REFUSED_ACTIONS):
        return False
    return (
        is_allowlisted_code_readonly_action(state)
        or is_allowlisted_research_readonly_action(state)
        or is_allowlisted_memory_readonly_action(state)
    )


def get_execution_refusal_reason(state: EvaRuntimeState) -> str:
    text = _intent(state)
    finding = state.safety_findings[-1] if state.safety_findings else {}
    if is_low_risk_status_action(state):
        return ""
    if finding.get("blocked"):
        return str(finding.get("reason") or "Blocked by guardrails.")
    if any(marker in text for marker in ("mcp", "model context protocol")):
        return "MCP execution is disabled in Phase 3."
    if any(marker in text for marker in ("playwright", "login to gmail")):
        return "Playwright execution is disabled in Phase 3."
    if any(marker in text for marker in ("click ", "type ", "button", "screen", "pyautogui", "desktop")):
        return "Desktop execution is disabled in Phase 3."
    if any(marker in text for marker in ("powershell", "shell", "cmd ", "terminal command", "run command", "run script")):
        return "Arbitrary shell is blocked in Phase 3."
    if any(marker in text for marker in ("install ", "pip " + "install", "package install")):
        return "Package install is not allowed in Phase 4 read-only execution."
    if any(marker in text for marker in ("logged in", "private page", "private account", "bypass login", "bypass paywall", "paywall", "hidden credential", "cookies", "localstorage", "sessionstorage", "scrape my logged-in", "gmail", "email", "private chat", "read chat", "chat history")):
        return "Private or logged-in page reading is not allowed in Phase 4 read-only execution."
    if any(marker in text for marker in ("send whatsapp", "send message", "post ", "submit", "purchase", "buy ")):
        return "Confirmation required for external message sending or posting; Phase 3 execution bridge refuses it."
    if "delete memory" in text or "forget memory" in text:
        return "Memory delete is not allowed in Phase 4 read-only execution."
    if "delete" in text:
        return "Override required for destructive or file-changing action; Phase 3 execution bridge refuses it."
    if any(marker in text for marker in ("move ", "rename", "write file", "edit file", "edit ", "write ")):
        return "File modification is not allowed in Phase 4 read-only execution."
    decision = (state.permission_decision or {}).get("decision")
    if decision == "ask_confirmation":
        return "Confirmation required for external message sending or another external-visible action; Phase 3 execution bridge refuses it."
    if decision == "ask_override":
        return "Override required for destructive or system-changing action; Phase 3 execution bridge refuses it."
    if is_allowlisted_browser_open_action(state):
        return ""
    if is_v2_readonly_action(state):
        return ""
    return _phase_refusal()


def browser_app_from_state(state: EvaRuntimeState) -> str | None:
    return _browser_app_key(state)


def _intent(state: EvaRuntimeState) -> str:
    return " ".join(str(state.normalized_intent or state.user_request or "").lower().strip().split())


def _action_types(state: EvaRuntimeState) -> set[str]:
    return {str(action.get("action_type") or "").strip() for action in state.proposed_actions if isinstance(action, dict)}


def _resource_executable(resource_id: str) -> bool:
    decision = evaluate_resource_by_id(resource_id)
    return bool(decision.executable_now and decision.status in {"allowed", "allowed_with_permission"})


def _readonly_reason(state: EvaRuntimeState) -> str:
    if state.selected_agent == "code":
        return "Allowed read-only workspace/code inspection through existing Eva Code Intelligence or Workspace Skills."
    if state.selected_agent == "research":
        return "Allowed read-only public/local research lookup through existing Eva research helpers."
    if state.selected_agent == "memory":
        return "Allowed read-only memory recall/status through existing local memory helpers."
    return "Allowed read-only v2 delegated action."


def _browser_app_key(state: EvaRuntimeState) -> str | None:
    text = _intent(state)
    if not text.startswith("open "):
        return None
    candidate = re.sub(r"^open\s+", "", text).strip()
    candidate = re.sub(r"\s+(?:on|in)\s+chrome$", "", candidate).strip()
    resolved = resolve_web_app(candidate)
    if not resolved:
        return None
    return str(resolved["key"])


def _phase_refusal() -> str:
    return "V2 execution bridge refused this action. Use v2 dry run/plan, or wait for a later permission-gated phase."
