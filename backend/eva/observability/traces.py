from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from .local_trace_store import LocalTraceStore


def _store(root: Path | None = None) -> LocalTraceStore:
    return LocalTraceStore(root=root)


def start_trace(request_id: str, user_request: str, root: Path | None = None) -> str:
    trace_id = f"trace_{request_id or uuid4().hex}"
    _store(root).append(trace_id, "trace_started", {"request_id": request_id, "user_request": user_request})
    return trace_id


def log_agent_selection(trace_id: str, agent_name: str, reason: str, root: Path | None = None) -> None:
    _store(root).append(trace_id, "agent_selected", {"agent_name": agent_name, "reason": reason})


def log_llm_call(trace_id: str, provider: str, model: str, prompt_summary: str, result_summary: str, root: Path | None = None) -> None:
    _store(root).append(trace_id, "llm_call", {"provider": provider, "model": model, "prompt_summary": prompt_summary, "result_summary": result_summary})


def log_tool_call(trace_id: str, tool_name: str, args_redacted: dict[str, Any], result_summary: str, root: Path | None = None) -> None:
    _store(root).append(trace_id, "tool_call", {"tool_name": tool_name, "args": args_redacted, "result_summary": result_summary})


def log_permission(trace_id: str, decision: dict[str, Any], root: Path | None = None) -> None:
    _store(root).append(trace_id, "permission", decision)


def log_verification(trace_id: str, verification: dict[str, Any], root: Path | None = None) -> None:
    _store(root).append(trace_id, "verification", verification)


def end_trace(trace_id: str, final_summary: str, root: Path | None = None) -> None:
    _store(root).append(trace_id, "trace_ended", {"final_summary": final_summary})


def traces_status() -> dict[str, Any]:
    status = _store().status()
    status["message"] = "Traces status: local JSONL trace store is active; remote tracing is disabled unless explicitly configured."
    return status
