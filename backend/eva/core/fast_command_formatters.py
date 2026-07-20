"""Result-formatting helpers for the typed-console fast-command dispatcher.

Split out of ``fast_commands.py`` in Phase 71 as a pure move: this module
holds the ``_format_*`` family (turning a raw tool/status result into the
text Eva actually says) plus ``_run_tool`` and ``_json_debug``, which exist
only to serve those formatters. ``_run_tool`` is the one function here whose
name doesn't start with ``_format_``; it is included because its entire job
is "call a tool, then hand the result to the right formatter below" -- it
has no caller besides ``maybe_handle_fast_command`` and no dependency besides
these formatters, so keeping it beside them avoids exposing all of them as
cross-module API just so a differently-named wrapper could live elsewhere.

The ``_format_*_ask_response`` family (formatting for ``eva ask`` intents
specifically) is NOT here -- those live in ``fast_command_ask.py`` next to
``_handle_eva_ask_command``, the only function that calls them.

No behavior changed: every function below is unmodified from its previous
body in ``fast_commands.py``, including existing local (lazy) imports.
"""
from __future__ import annotations

import json

from ..core.web_context import remember_web_results
from ..tools.registry import ToolRegistry


AGENT_STATUS_SUMMARY = {
    "mode": "Agentic v2",
    "loop": "bounded plan -> act -> observe -> reflect -> stop/continue",
    "safety": {
        "arbitrary_shell": False,
        "camera": False,
        "always_on_screen": False,
        "power_actions_need_confirmation": True,
        "tools_are_whitelisted": True,
    },
    "features": [
        "initial task plan",
        "step-by-step safe tool execution",
        "observation tracking",
        "reflection after tool results",
        "SQLite chat/event memory",
        "user facts via 'remember that ...'",
        "repeat-action stop",
        "budget limits for tools, web searches, and screen captures",
    ],
}


def _json_debug(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def _format_agent_status(*, raw: bool = False) -> str:
    if raw:
        return _json_debug(AGENT_STATUS_SUMMARY)
    safety = AGENT_STATUS_SUMMARY["safety"]
    return "\n".join(
        [
            "Agent status: Agentic v2 is available.",
            "Loop: bounded plan -> act -> observe -> reflect -> continue/stop.",
            "Verification: tool observations and reflections are tracked before Eva reports completion.",
            "Safety: arbitrary shell is blocked, camera is off, always-on screen watching is off, and power actions require confirmation.",
            f"Limits: {len(AGENT_STATUS_SUMMARY['features'])} tracked agent features are enabled. Say `agent status raw` for debug JSON.",
        ]
    )


def _format_tools_status(tools: ToolRegistry, *, raw: bool = False) -> str:
    specs = tools.list_tools()
    if raw:
        return _json_debug({"tool_count": len(specs), "tools": specs})
    categories: dict[str, int] = {}
    risky: dict[str, int] = {}
    confirmation_count = 0
    rollback_count = 0
    for spec in specs:
        categories[str(spec.get("category") or "general")] = categories.get(str(spec.get("category") or "general"), 0) + 1
        risky[str(spec.get("risk") or "low")] = risky.get(str(spec.get("risk") or "low"), 0) + 1
        confirmation_count += 1 if spec.get("requires_confirmation") else 0
        rollback_count += 1 if spec.get("supports_rollback") else 0
    category_text = ", ".join(f"{name}: {count}" for name, count in sorted(categories.items()))
    risk_text = ", ".join(f"{name}: {count}" for name, count in sorted(risky.items()))
    return "\n".join(
        [
            f"Tools status: Eva has {len(specs)} registered tool specs in the local tool registry.",
            f"Categories: {category_text}.",
            f"Risk levels: {risk_text}.",
            f"Permission-aware tools: {confirmation_count} require confirmation/override; {rollback_count} advertise rollback support.",
            "No arbitrary shell tool is registered as a default path. Say `tools status raw` for debug JSON.",
        ]
    )


def _format_permissions_status(*, raw: bool = False) -> str:
    payload = {
        "safe_local_actions": "allow",
        "privacy_screen_file_chat_reads": "ask_override",
        "external_messages_posts_forms": "ask_confirmation",
        "destructive_file_or_system_changes": "ask_override",
        "power_actions": "ask_confirmation",
        "shell_default": "hard_block",
        "override_phrase": "confirm override",
        "override_expires_after_seconds": 120,
        "hard_blocks": ["credential theft", "spyware behavior", "malware-like actions", "illegal harmful requests"],
    }
    if raw:
        return _json_debug(payload)
    return "\n".join(
        [
            "Permissions status: Eva's local permission gate is active.",
            "Allowed: safe local reads and bounded visible UI actions.",
            "Confirmation required: external messages, posts, form submits, and guarded power actions.",
            "Override required: privacy-sensitive reads, destructive file actions, and system-changing actions. Override phrase: `confirm override`.",
            "Hard blocked: credential access, spying, malware-like behavior, illegal harmful requests, and arbitrary shell by default.",
            "Say `permissions status raw` for debug JSON.",
        ]
    )


def _format_code_status(result: object, *, raw: bool = False) -> str:
    if raw:
        return _json_debug(result)
    if not isinstance(result, dict) or not result.get("ok"):
        return f"Code status: unavailable safely ({result.get('error') if isinstance(result, dict) else 'unknown error'})."
    indexed = "ready" if result.get("indexed") else "not built yet"
    return (
        f"Code status: safe code index is {indexed}. "
        f"Indexed files: {result.get('indexed_files', 0)}. "
        f"Secrets indexed: {'yes' if result.get('secrets_indexed') else 'no'}. "
        "Say `code status raw` for debug JSON."
    )


def _format_research_status(result: object, *, raw: bool = False) -> str:
    if raw:
        return _json_debug(result)
    if not isinstance(result, dict) or not result.get("ok"):
        return f"Research status: unavailable safely ({result.get('error') if isinstance(result, dict) else 'unknown error'})."
    return (
        "Research status: local SQLite research knowledge is available. "
        f"Topics: {result.get('topic_count', 0)}. Sources: {result.get('item_count', 0)}. "
        f"Notes: {result.get('note_count', 0)}. Sessions: {result.get('session_count', 0)}. "
        "Say `research status raw` for debug JSON."
    )


def _format_eva_v2_status() -> str:
    from ..runtime.feature_flags import eva_v2_runtime_status
    from ..runtime.graph import is_langgraph_available

    status = eva_v2_runtime_status()
    flags = status.get("flags") if isinstance(status.get("flags"), dict) else {}
    enabled = "enabled" if status.get("enabled") else "installed but disabled"
    return "\n".join(
        [
            f"Eva v2 runtime status: {enabled}.",
            "EVA_V2_RUNTIME_ENABLED=false, so the current Eva routing and Agentic v2 loop remain active by default."
            if not status.get("enabled")
            else "EVA_V2_RUNTIME_ENABLED=true, so safe demo requests may pass through the v2 skeleton.",
            f"Optional graph: LangGraph {'available' if is_langgraph_available() else 'not installed or disabled'}; flag EVA_V2_LANGGRAPH_ENABLED={str(flags.get('langgraph_enabled', False)).lower()}.",
            "Phase 1 scope: typed state/actions, specialist-agent selection, guardrail hooks, local traces, vector-memory interfaces, and optional automation adapters.",
        ]
    )


def _format_agents_status() -> str:
    from ..runtime.supervisor import supervisor_status

    status = supervisor_status()
    agents = status.get("agents") if isinstance(status.get("agents"), list) else []
    lines = [f"Specialist agents status: {len(agents)} v2 skeleton agents are registered."]
    for item in agents:
        if isinstance(item, dict):
            lines.append(f"- {item.get('name')}: {item.get('delegated_core')}")
    lines.append("They propose/delegate through existing Eva systems; they do not replace the current loop yet.")
    return "\n".join(lines)


def _format_guardrails_status() -> str:
    from ..guardrails.llm_guard_adapter import is_llm_guard_available
    from ..runtime.feature_flags import get_v2_feature_flags

    flags = get_v2_feature_flags()
    available = is_llm_guard_available()
    enabled = bool(flags.llm_guard_enabled and available)
    return "\n".join(
        [
            f"Guardrails status: LLM Guard package is {'available' if available else 'not installed'}; adapter enabled: {enabled}.",
            "Fallback guardrails are active for Phase 1: secret redaction, prompt-injection phrase detection, suspicious tool-call checks, and output-safety checks.",
            "The Cloud Context Firewall and Permission Gate remain the authority for private local context and risky actions.",
        ]
    )


def _format_vector_memory_status() -> str:
    from ..vector_memory.retriever import vector_memory_status

    status = vector_memory_status()
    return "\n".join(
        [
            f"Vector memory status: interfaces installed, primary backend is {status.get('primary')}.",
            f"Chroma enabled: {status.get('chroma', {}).get('enabled') if isinstance(status.get('chroma'), dict) else False}. Qdrant enabled: {status.get('qdrant', {}).get('enabled') if isinstance(status.get('qdrant'), dict) else False}.",
            "Vector memory is disabled by default; Eva keeps using local SQLite memory/research retrieval unless explicitly configured.",
        ]
    )


def _format_traces_status() -> str:
    from ..observability.langfuse_adapter import langfuse_status
    from ..observability.traces import traces_status

    local = traces_status()
    langfuse = langfuse_status()
    return "\n".join(
        [
            f"Traces status: local trace store is {local.get('backend')} at {local.get('path')}.",
            f"Langfuse enabled: {langfuse.get('enabled')} ({langfuse.get('message')}).",
            "Trace payloads are redacted before local write; remote tracing is disabled unless explicitly configured later.",
        ]
    )


def _format_traces_list() -> str:
    from ..observability.traces import list_traces

    traces = list_traces(limit=10)
    if not traces:
        return "No recent traces found. Tracing is off by default; enable EVA_TRACING_ENABLED to record traces."
    lines = ["Recent traces:"]
    for trace in traces:
        request = str(trace.get("request") or "").strip()
        if len(request) > 80:
            request = request[:80] + "…"
        lines.append(f"- {trace.get('trace_id')} ({trace.get('event_count')} events): {request or '(no request captured)'}")
    return "\n".join(lines)


def _format_trace_show(trace_id: str) -> str:
    from ..observability.traces import read_trace

    trace = read_trace(trace_id)
    if not trace.get("found"):
        return f"No trace found for `{trace_id}`."
    lines = [f"Trace {trace_id}:"]
    for event in trace.get("events", []):
        event_type = str(event.get("type") or "unknown")
        payload = event.get("payload")
        preview = json.dumps(payload, ensure_ascii=False, default=str) if payload is not None else ""
        if len(preview) > 120:
            preview = preview[:120] + "…"
        lines.append(f"- {event_type}: {preview}")
    return "\n".join(lines)


def _format_evals_status() -> str:
    from ..evals import benchmark_adapters, run_offline_evals

    report = run_offline_evals()
    lines = [report.summary_text()]
    lines.append("Benchmark availability (all inert/gated unless explicitly opted in via env flags):")
    for adapter in benchmark_adapters():
        status = adapter.availability()
        lines.append(f"- {status.get('name')}: available={status.get('available')} ({status.get('reason')})")
    return "\n".join(lines)


def _format_activation_status() -> str:
    from ..runtime.activation import current_activation_status

    status = current_activation_status()
    mind = status["mind"]
    hands = status["hands_external"]

    def _state(flag: bool) -> str:
        return "ON" if flag else "off"

    lines = [
        f"Activation profile: {status['profile']} (set EVA_PROFILE to change).",
        "Mind capabilities (a profile may enable these):",
        f"- tracing: {_state(mind['tracing'])}",
        f"- vector_memory: {_state(mind['vector_memory'])}",
        f"- native_function_calling: {_state(mind['native_function_calling'])}",
        "Hands & external (manual only — never auto-enabled by a profile):",
        f"- real_input: {_state(hands['real_input'])}",
        f"- browser: {_state(hands['browser'])}",
        f"- mcp: {_state(hands['mcp'])}",
        str(status["note"]),
    ]
    return "\n".join(lines)


def _format_exercise_status() -> str:
    from ..evals import run_offline_exercise

    return run_offline_exercise().summary_text()


def _format_automation_adapters_status() -> str:
    from ..browser_automation.playwright_driver import playwright_status
    from ..desktop_automation.pyautogui_driver import pyautogui_status

    playwright = playwright_status()
    pyautogui = pyautogui_status()
    return "\n".join(
        [
            f"Automation adapters status: Playwright enabled={playwright.get('enabled')} available={playwright.get('available')}.",
            f"PyAutoGUI strict adapter enabled={pyautogui.get('enabled')} available={pyautogui.get('available')}.",
            "Existing Chrome/Desktop skills remain primary. Optional adapters refuse unsafe reads, raw coordinate clicks, and unconfirmed external/destructive actions.",
        ]
    )


def _format_web_search_result(result: object) -> str:
    if not isinstance(result, dict):
        return str(result)
    query = result.get("query") or "your search"
    if result.get("ok") and result.get("provider") == "tavily":
        personal_profile = _looks_like_personal_profile_query(str(query))
        lines = [
            "I found possible matches, but I can't assume which one is yours."
            if personal_profile
            else f"I searched Tavily for: {query}."
        ]
        answer = str(result.get("answer") or "").strip()
        if answer and not personal_profile:
            lines.append(answer)
        results = result.get("results") or []
        if isinstance(results, list) and results:
            lines.append("Options:" if personal_profile else "Top results:")
            for item in results[:5]:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or "Untitled")
                url = str(item.get("url") or "")
                lines.append(f"- {title}: {url}" if url else f"- {title}")
        return "\n".join(lines)
    if result.get("fallback") == "browser":
        reason = result.get("error") or "unavailable"
        return f"Tavily search was {reason}, so I opened a browser search for: {query}."
    return str(result)


def _format_screen_result(result: object) -> str:
    if not isinstance(result, dict):
        return str(result)
    if not result.get("ok"):
        summary = str(result.get("summary") or "").strip()
        if result.get("rate_limited") and summary:
            return summary
        return f"I captured the screen once, but vision analysis failed: {result.get('error') or 'unknown error'}."
    summary = str(result.get("summary") or "").strip()
    issue = str(result.get("possible_issue") or "").strip()
    actions = result.get("suggested_actions") or []
    chunks = [summary or "I analyzed the screen, but the image is unclear."]
    if issue:
        chunks.append(f"Possible issue: {issue}")
    if isinstance(actions, list) and actions:
        chunks.append("Try this: " + "; ".join(str(item) for item in actions[:3] if str(item).strip()))
    return " ".join(chunks)


def _format_workspace_result(result: object, *, mode: str = "generic") -> str:
    if not isinstance(result, dict):
        return str(result)
    if not result.get("ok"):
        return f"I refused that workspace request safely: {result.get('error') or 'unknown error'}."

    if mode == "status" or "exclude_dirs" in result:
        return json.dumps(result, indent=2)

    if "sections" in result:
        lines = ["Here is Eva's project shape:"]
        for section in result.get("sections") or []:
            if not isinstance(section, dict):
                continue
            folder = section.get("folder")
            description = section.get("description")
            lines.append(f"- {folder}: {description}")
            notable = section.get("notable_files") or []
            if notable:
                lines.append("  Key files: " + ", ".join(str(item) for item in notable[:5]))
        lines.append("Workspace scan is read-only and skips secrets/runtime folders.")
        return "\n".join(lines)

    if "matches" in result:
        matches = result.get("matches") or []
        if not matches:
            return f"I searched the Eva workspace for '{result.get('query')}', but did not find a safe match."
        lines = [f"I searched the Eva workspace for '{result.get('query')}'. Top matches:"]
        for item in matches[:8]:
            if not isinstance(item, dict):
                continue
            lines.append(f"- {item.get('path')}:{item.get('line')} - {item.get('snippet')}")
        return "\n".join(lines)

    if "files" in result:
        files = result.get("files") or []
        lines = [f"I found {len(files)} safe workspace files" + (" in " + str(result.get("path")) if result.get("path") else "") + ":"]
        for item in files[:80]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('path')} ({item.get('size')} bytes)")
        if result.get("truncated"):
            lines.append("More files exist, but I stopped at the configured scan limit.")
        return "\n".join(lines)

    if "content" in result:
        content = str(result.get("content") or "")
        snippet = content[:6000]
        suffix = "\n\n[truncated]" if result.get("truncated") else ""
        return f"Read `{result.get('path')}` safely:\n```text\n{snippet}\n```{suffix}"

    if "summary" in result:
        return f"{result.get('summary')}"

    return json.dumps(result, indent=2)


def _format_code_index_status(result: object) -> str:
    if not isinstance(result, dict) or not result.get("ok"):
        error = result.get("error") if isinstance(result, dict) else "unknown error"
        return f"Code index v2 status unavailable safely: {error}."
    if not result.get("indexed"):
        return "Code index v2 status: no local metadata cache has been built yet. Run `code index refresh` to build it."
    return (
        "Code index v2 status: ready. "
        f"Indexed files: {result.get('indexed_files', 0)}. "
        f"Skipped: {result.get('skipped', 0)}. "
        "Cache: local metadata only. Full file contents stored: no. Secrets indexed: no."
    )


def _format_code_index_refresh(result: object) -> str:
    if not isinstance(result, dict) or not result.get("ok"):
        error = result.get("error") if isinstance(result, dict) else "unknown error"
        return f"Code index v2 refresh failed safely: {error}."
    return (
        "Code index v2 refreshed. "
        f"Indexed {result.get('indexed_files', 0)} safe files and skipped {result.get('skipped', 0)} blocked/unsupported files. "
        "The cache stores metadata only, not full file contents."
    )


def _format_code_index_search(result: object) -> str:
    if not isinstance(result, dict) or not result.get("ok"):
        error = result.get("error") if isinstance(result, dict) else "unknown error"
        return f"Code index v2 search refused safely: {error}."
    matches = result.get("matches") or []
    if not matches:
        return f"Code index v2 matches for `{result.get('query')}`: none found in the safe metadata index."
    lines = [f"Code index v2 matches for `{result.get('query')}`:"]
    for item in matches[:8]:
        if isinstance(item, dict):
            lines.append(f"- {item.get('path')}: {item.get('summary')}")
    return "\n".join(lines)


def _format_code_index_symbols(result: object) -> str:
    if not isinstance(result, dict) or not result.get("ok"):
        error = result.get("error") if isinstance(result, dict) else "unknown error"
        return f"Code index v2 symbol search refused safely: {error}."
    matches = result.get("matches") or []
    if not matches:
        return f"Code index v2 symbols for `{result.get('query')}`: none found."
    lines = [f"Code index v2 symbols for `{result.get('query')}`:"]
    for item in matches[:10]:
        if isinstance(item, dict):
            lines.append(f"- {item.get('name')} ({item.get('kind')}) in {item.get('path')}:{item.get('line')}")
    return "\n".join(lines)


def _format_code_index_workspace(result: object) -> str:
    if not isinstance(result, dict) or not result.get("ok"):
        error = result.get("error") if isinstance(result, dict) else "unknown error"
        return f"Workspace summary unavailable safely: {error}."
    lines = ["Workspace summary:"]
    for area in result.get("major_areas") or []:
        lines.append(f"- {area}")
    lines.append(f"Indexed safe files: {result.get('indexed_files', 0)}.")
    lines.append(str(result.get("safety") or "Code index stores metadata only."))
    return "\n".join(lines)


def _format_code_index_file_summary(result: object) -> str:
    if not isinstance(result, dict) or not result.get("ok"):
        error = result.get("error") if isinstance(result, dict) else "unknown error"
        return f"Code file summary refused safely: {error}."
    lines = [
        f"Code file summary for `{result.get('path')}`:",
        str(result.get("summary") or "Summary unavailable."),
        "Summary-only local read; full file contents were not returned.",
    ]
    symbols = result.get("symbols") or []
    if symbols:
        lines.append("Symbols: " + ", ".join(str(symbol) for symbol in symbols[:20]))
    return "\n".join(lines)


def _format_code_result(result: object, *, mode: str = "generic") -> str:
    if not isinstance(result, dict):
        return str(result)
    if not result.get("ok"):
        return f"Code intelligence refused that safely: {result.get('error') or 'unknown error'}."

    if mode == "status":
        return _format_code_status(result)

    if mode == "reindex":
        return f"Code index refreshed. Indexed {result.get('indexed_files', 0)} safe files. Skipped {result.get('skipped', 0)} blocked/unsupported files."

    if mode == "project_map":
        lines = [f"Code project map: {result.get('indexed_files', 0)} indexed files."]
        for module in result.get("modules") or []:
            if isinstance(module, dict):
                lines.append(f"- {module.get('folder')}: {module.get('description')} ({module.get('file_count')} files)")
        return "\n".join(lines)

    if mode == "search":
        matches = result.get("matches") or []
        if not matches:
            return f"I searched the code index for '{result.get('query')}', but found no safe matches."
        lines = [f"Code matches for '{result.get('query')}':"]
        for item in matches[:8]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('path')}: {item.get('summary')}")
        return "\n".join(lines)

    if mode == "find_symbol":
        matches = result.get("matches") or []
        if not matches:
            return f"I couldn't find symbol `{result.get('symbol')}` in the safe code index."
        lines = [f"Symbol matches for `{result.get('symbol')}`:"]
        for item in matches[:10]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('name')} ({item.get('kind')}) in {item.get('path')}:{item.get('line')}")
        return "\n".join(lines)

    if mode == "explain_feature":
        lines = [str(result.get("summary") or "Feature locations found.")]
        related = result.get("related_files") or []
        if related:
            lines.append("Relevant files:")
            lines.extend(f"- {path}" for path in related[:10])
        return "\n".join(lines)

    if mode == "debug_traceback":
        lines = [
            f"Error: {result.get('exception_type') or 'unknown'} - {result.get('exception_message') or 'no message'}",
            str(result.get("likely_cause") or "Likely cause needs inspection."),
        ]
        likely = result.get("likely_files") or []
        if likely:
            lines.append("Files to inspect:")
            lines.extend(f"- {path}" for path in likely[:8])
        tests = result.get("suggested_tests") or []
        if tests:
            lines.append("Tests to run:")
            lines.extend(f"- {test}" for test in tests[:4])
        return "\n".join(lines)

    if mode == "plan_change":
        lines = [f"Patch plan for: {result.get('goal')}"]
        files = result.get("likely_files") or []
        if files:
            lines.append("Likely files:")
            lines.extend(f"- {path}" for path in files[:10])
        steps = result.get("proposed_steps") or []
        if steps:
            lines.append("Steps:")
            lines.extend(f"- {step}" for step in steps[:8])
        tests = result.get("tests_to_run") or []
        if tests:
            lines.append("Tests:")
            lines.extend(f"- {test}" for test in tests[:5])
        risks = result.get("risks") or []
        if risks:
            lines.append("Risks:")
            lines.extend(f"- {risk}" for risk in risks[:5])
        lines.append("This is planning-only. I will not edit files unless you explicitly ask.")
        return "\n".join(lines)

    return json.dumps(result, indent=2)


def _format_research_result(result: object, *, mode: str = "generic") -> str:
    if not isinstance(result, dict):
        return str(result)
    if not result.get("ok"):
        if result.get("fallback") == "browser":
            return f"Tavily is unavailable for research right now, so only limited browser fallback is available for: {result.get('query')}."
        return f"Research request failed safely: {result.get('error') or 'unknown error'}."

    if mode == "status" or "topic_count" in result:
        return _format_research_status(result)

    if mode == "start_topic" or "topic" in result and "message" in result:
        return str(result.get("message") or f"Research topic ready: {result.get('topic')}")

    if mode == "save_note":
        return str(result.get("message") or f"Saved research note for {result.get('topic')}.")

    if mode == "recall":
        matches = result.get("matches") or []
        topic = result.get("topic")
        if not matches:
            return f"I don't have saved research on {topic} yet."
        lines = [f"Here is what I know locally about {topic}:"]
        for item in matches[:5]:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "source":
                lines.append(f"- {item.get('title')}: {item.get('url')} - {item.get('text')}")
            else:
                lines.append(f"- {item.get('text')}")
        return "\n".join(lines)

    if mode == "summary" or "summary" in result:
        return str(result.get("summary") or result)

    if mode == "web":
        lines = [f"Saved fresh research for {result.get('topic')}: {result.get('query')}"]
        answer = str(result.get("answer") or "").strip()
        if answer:
            lines.append(answer)
        saved = result.get("saved_results") or []
        if saved:
            lines.append("Sources saved:")
            for item in saved[:5]:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('title')}: {item.get('url')}")
        return "\n".join(lines)

    return json.dumps(result, indent=2)


def _format_window_result(result: object, *, mode: str = "generic") -> str:
    if not isinstance(result, dict) or not result.get("ok"):
        error = result.get("error") if isinstance(result, dict) else "unknown error"
        return f"I couldn't read that desktop state right now: {error}."
    if mode == "active":
        window = result.get("window") if isinstance(result.get("window"), dict) else {}
        return f"You're on: {window.get('title') or 'unknown window'} ({window.get('process_name') or 'unknown process'})."
    if mode == "list":
        windows = result.get("windows") if isinstance(result.get("windows"), list) else []
        if not windows:
            return "I don't see any visible app windows from this context."
        lines = ["Open windows:"]
        for item in windows[:12]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('title') or 'Untitled'} ({item.get('process_name') or 'unknown'})")
        return "\n".join(lines)
    if mode in {"focus", "minimize", "maximize", "close_safe"}:
        window = result.get("window") if isinstance(result.get("window"), dict) else {}
        title = window.get("title") or result.get("query") or "that window"
        if mode == "focus" and result.get("verified") is False:
            return f"I tried switching to {title}, but Windows did not confirm focus."
        action = {"focus": "focused", "minimize": "minimized", "maximize": "maximized", "close_safe": "closed"}[mode]
        return f"Done, {action} {title}."
    if mode == "observe":
        active = result.get("active_window_title") or "unknown"
        count = len(result.get("open_windows") or []) if isinstance(result.get("open_windows"), list) else 0
        notes = result.get("notes") or []
        suffix = f" Notes: {' '.join(str(item) for item in notes[:2])}" if notes else ""
        return f"Desktop observed. Active window: {active}. Visible windows: {count}.{suffix}"
    if mode == "verify":
        message = str(result.get("message") or "").strip()
        if message:
            return message
        return "Verified." if result.get("verified") else "I couldn't verify that from Windows."
    return json.dumps(result, indent=2)


def _format_browser_result(result: object, *, mode: str = "generic") -> str:
    if not isinstance(result, dict):
        return str(result)
    if not result.get("ok"):
        if result.get("safety_blocked"):
            return str(result.get("summary") or "I refused to read that page automatically because it looks private or sensitive.")
        return str(result.get("summary") or f"Browser action failed safely: {result.get('error') or 'unknown error'}.")
    if mode == "status":
        detected = "yes" if result.get("browser_detected") else "no"
        known = result.get("known_current_url") or "unknown"
        windows = result.get("open_browser_windows") or []
        return f"Browser detected: {detected}. Known page: {known}. Browser windows visible: {len(windows) if isinstance(windows, list) else 0}."
    if mode == "current_page":
        title = result.get("current_title") or result.get("active_window_title") or "unknown page"
        url = result.get("current_url")
        if result.get("verified") is False or result.get("stale"):
            message = str(result.get("message") or "").strip()
            if message:
                return message
            known = result.get("known_current_url") or result.get("url")
            return "I can't verify the current Chrome page right now." + (f" Last known page was {known}." if known else "")
        if url:
            return f"Current browser page: {title}\n{url}"
        return f"I can see the browser title: {title}. I do not have the current tab URL unless you opened it through Eva or send me the URL."
    if mode == "summarize_page":
        title = result.get("current_title") or "Current page"
        summary = result.get("page_summary") or "I could not extract readable page text."
        url = result.get("current_url") or ""
        return f"{title}: {summary}" + (f"\n{url}" if url else "")
    if mode == "extract_links":
        links = result.get("extracted_links") or []
        if not links:
            return "I did not find readable links on that safe public page."
        lines = [f"Found {len(links)} links:"]
        for item in links[:12]:
            if isinstance(item, dict):
                lines.append(f"- {item.get('text') or 'Link'}: {item.get('url')}")
        return "\n".join(lines)
    if mode == "save_page_to_research":
        return str(result.get("message") or f"Saved {result.get('saved_count', 0)} browser page source(s) to research.")
    if mode == "search":
        remember = _format_web_search_result(result)
        return remember if remember != str(result) else f"Opened browser search for {result.get('query')}."
    if mode == "open_url":
        return "Done, opened that in Chrome." if result.get("opened") else "I tried to open that URL, but could not confirm it."
    if mode == "observe":
        return _format_browser_result(result, mode="current_page")
    return json.dumps(result, indent=2)


def _looks_like_personal_profile_query(text: str) -> bool:
    lowered = text.lower()
    return ("ankit l" in lowered or "my profile" in lowered) and "profile" in lowered


def _run_tool(tools: ToolRegistry, name: str, session_context: dict | None = None, **kwargs: object) -> tuple[str, str]:
    try:
        result = tools.run(name, **kwargs)
        if name in {"open_app", "open_folder", "open_url"}:
            target = str(kwargs.get("app") or kwargs.get("app_name") or kwargs.get("folder") or kwargs.get("folder_name") or kwargs.get("url") or "")
            try:
                verification = tools.run("verify_last_action", tool=name, target=target)
            except Exception:
                verification = None
            if isinstance(verification, dict):
                if name == "open_app":
                    return (f"Done, {target} is open." if verification.get("verified") else f"Done, opened {target}, but I couldn't verify the window."), "desktop-tool"
                if name == "open_folder":
                    return (f"Done, {target} is open." if verification.get("verified") else f"Done, opened {target}, but I couldn't verify the folder window."), "desktop-tool"
                if name == "open_url":
                    return ("Done, opened that in Chrome." if verification.get("verified") else "Done, opened the link, but I couldn't verify the browser URL from Windows."), "desktop-tool"
        if name == "web_search":
            remember_web_results(session_context, result)
            return _format_web_search_result(result), "desktop-tool"
        if name == "analyze_screen":
            return _format_screen_result(result), "desktop-tool"
        if name.startswith("window_"):
            return _format_window_result(result, mode=name.removeprefix("window_")), "desktop-tool"
        if name == "app.focus":
            # Same result shape as window_focus (both call focus_window), so
            # the existing "focus" formatting mode -- including the honest
            # "Windows did not confirm focus" message -- applies unchanged.
            return _format_window_result(result, mode="focus"), "desktop-tool"
        if name == "desktop_observe":
            return _format_window_result(result, mode="observe"), "desktop-tool"
        if name == "verify_last_action":
            return _format_window_result(result, mode="verify"), "desktop-tool"
        if name.startswith("browser_"):
            mode = name.removeprefix("browser_")
            if name == "browser_search":
                remember_web_results(session_context, result)
                mode = "search"
            return _format_browser_result(result, mode=mode), "browser-tool"
        if name.startswith("chrome_") or name == "browser_open_result_and_verify":
            if isinstance(result, dict):
                message = str(result.get("message") or result.get("summary") or "").strip()
                if message:
                    return message, "browser-tool"
                if name == "chrome_copy_current_url" and not result.get("ok"):
                    return "I can't verify the current Chrome page right now, so I did not copy a stale URL.", "browser-tool"
            return _format_browser_result(result, mode=name), "browser-tool"
        if name.startswith("code_"):
            return _format_code_result(result, mode=name.removeprefix("code_")), "code-tool"
        if name.startswith("workspace_"):
            return _format_workspace_result(result, mode=name.removeprefix("workspace_")), "workspace-tool"
        if name.startswith("research_"):
            return _format_research_result(result, mode=name.removeprefix("research_")), "research-tool"
        return str(result), "desktop-tool"
    except Exception as exc:
        return f"I tried, but Windows reported: {exc}", "desktop-tool"
