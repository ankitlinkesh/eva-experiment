from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from ..agent.executor import ToolExecutor, ToolExecutionResult
from ..agent.planner import PlannerDecision, PlannerError, ToolCallPlanner
from ..agent.runner import run_agentic_task
from ..agent.policies import is_agentic_intent
from ..core.fast_commands import maybe_handle_fast_command
from ..llm.router import complete_with_fallback
from ..models.gemini import GeminiClient
from ..models.ollama import OllamaClient
from ..models.router import ModelRoute, select_model
from ..screen.capture import capture_primary_screen_jpeg
from ..tools.registry import ToolRegistry


router = APIRouter()
tools = ToolRegistry()
executor = ToolExecutor(tools)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    source: str
    requires_confirmation: bool = False
    action: str | None = None


def _json_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"


def _source(route: ModelRoute) -> str:
    return f"{route.provider}:{route.model} ({route.reason})"


def _decision_payload(decision: PlannerDecision) -> dict:
    return {
        "type": decision.type,
        "reason": decision.reason,
        "tool_calls": [{"tool": call.tool, "args": call.args} for call in decision.tool_calls],
        "final_response": decision.final_response,
        "requires_confirmation": decision.requires_confirmation,
        "action": decision.action,
        "continue_after_tools": decision.continue_after_tools,
    }


def _results_payload(results: list[ToolExecutionResult]) -> list[dict]:
    return [result.as_dict() for result in results]


def _safe_log(memory, session_id: str, kind: str, payload: dict) -> None:
    try:
        memory.log_event(session_id, kind, payload)
    except Exception:
        # Logging should never break command execution.
        return


async def _chat_with_route(message: str, history: list[dict[str, str]], route: ModelRoute, settings) -> str:
    if route.provider == "gemini":
        return await GeminiClient(settings.models).chat(message, history=history, model=route.model)
    return await OllamaClient(settings.models).chat(message, history=history, model=route.model)


async def _stream_with_route(message: str, history: list[dict[str, str]], route: ModelRoute, settings) -> AsyncIterator[str]:
    if route.provider == "gemini":
        # Use the reliable non-SSE Gemini endpoint first; local Ollama still streams token-by-token.
        yield await GeminiClient(settings.models).chat(message, history=history, model=route.model)
        return
    async for token in OllamaClient(settings.models).stream_chat(message, history=history, model=route.model):
        yield token


async def _fallback_answer(message: str, history: list[dict[str, str]], settings) -> tuple[str, str]:
    route = select_model(message, settings.models)
    try:
        return await _chat_with_route(message, history, route, settings), _source(route)
    except RuntimeError as exc:
        fallback = ModelRoute("ollama", settings.models.fast_model, "fallback-local")
        try:
            return await _chat_with_route(message, history, fallback, settings), f"{_source(fallback)} after {_source(route)} failed"
        except RuntimeError:
            return f"I tried the smart brain and local fallback, but both failed. First error: {exc}", "model-error"


async def _synthesize_tool_response(message: str, results: list[ToolExecutionResult], history: list[dict[str, str]], settings) -> tuple[str, str]:
    payload = _results_payload(results)
    prompt = (
        "You are Eva. Summarize these tool execution results naturally and briefly. "
        "Be honest about failures and do not claim unavailable capabilities. "
        "If web_search returned Tavily results, summarize only the provided answer/results, list the top 3 to 5 titles with URLs, "
        "and mention browser fallback only when the result says fallback=browser. Do not invent facts not present in the tool JSON.\n\n"
        f"User request: {message}\n"
        f"Tool results JSON: {json.dumps(payload, ensure_ascii=False)}"
    )
    routed = await complete_with_fallback(
        [
            {"role": "system", "content": "You are Eva. Write concise final user-facing responses from safe local tool results."},
            {"role": "user", "content": prompt},
        ],
        settings.models,
        purpose="final_response",
        temperature=0.2,
        max_tokens=700,
    )
    if routed.response.ok and routed.response.text.strip():
        return routed.response.text.strip(), f"{routed.response.provider}:{routed.response.model} (tool-synthesis)"
    return _local_tool_summary(results), "tool-summary"


def _format_tavily_summary(result: dict) -> str:
    query = result.get("query") or "your search"
    if result.get("ok") and result.get("provider") == "tavily":
        lines = [f"I searched Tavily for: {query}."]
        answer = str(result.get("answer") or "").strip()
        if answer:
            lines.append(answer)
        items = result.get("results") or []
        if isinstance(items, list) and items:
            lines.append("Top results:")
            for item in items[:5]:
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


def _local_tool_summary(results: list[ToolExecutionResult]) -> str:
    if not results:
        return "I did not run any tools."
    chunks = []
    for result in results:
        if result.requires_confirmation:
            chunks.append(f"{result.tool} needs confirmation before {result.action}.")
        elif result.ok:
            if result.tool == "web_search" and isinstance(result.result, dict):
                chunks.append(_format_tavily_summary(result.result))
            else:
                chunks.append(f"{result.tool}: {result.result}")
        else:
            chunks.append(f"{result.tool} failed: {result.error}")
    return "Done. " + " ".join(chunks)


@router.get("/health")
async def health(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "ok": True,
        "name": "Eva",
        "model": settings.models.ollama_model,
        "fast_model": settings.models.fast_model,
        "deep_model": settings.models.deep_model,
        "smart_enabled": settings.models.smart_enabled,
        "smart_provider": settings.models.smart_provider,
        "smart_model": settings.models.smart_model,
        "screen_capture": settings.features.screen_capture,
        "voice_enabled": settings.features.voice_enabled,
        "camera_always_on": settings.features.camera_always_on,
    }


@router.get("/tools")
async def list_tools() -> dict:
    return {"tools": tools.list_tools(), "planner_tools": tools.planner_specs()}


@router.post("/tools/{tool_name}")
async def run_tool(tool_name: str, body: dict | None = None) -> dict:
    try:
        result = tools.run(tool_name, **(body or {}))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"tool": tool_name, "result": result}


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    session_id = payload.session_id or uuid4().hex
    memory = request.app.state.memory
    settings = request.app.state.settings

    fast = maybe_handle_fast_command(payload.message, tools)
    if fast is not None:
        reply, source = fast
        memory.add_message(session_id, "user", payload.message)
        memory.add_message(session_id, "assistant", reply)
        _safe_log(memory, session_id, "deterministic_command", {"source": source, "reply": reply})
        return ChatResponse(session_id=session_id, reply=reply, source=source)

    if is_agentic_intent(payload.message):
        history = memory.recent_messages(session_id)
        memory.add_message(session_id, "user", payload.message)
        result = await run_agentic_task(
            payload.message,
            {
                "settings": settings,
                "registry": tools,
                "executor": executor,
                "memory": memory,
                "session_id": session_id,
                "history": history,
                "execute_tools": True,
            },
        )
        reply = result.get("final_response") or "I stopped the task without a final response."
        memory.add_message(session_id, "assistant", reply)
        _safe_log(memory, session_id, "agent_task_result", {"task_id": result.get("task_id"), "status": result.get("status"), "safety_stops": result.get("safety_stops")})
        return ChatResponse(
            session_id=session_id,
            reply=reply,
            source="agent-runner",
            requires_confirmation=bool(result.get("requires_confirmation")),
            action=result.get("action"),
        )


    history = memory.recent_messages(session_id)
    memory.add_message(session_id, "user", payload.message)

    try:
        decision = await ToolCallPlanner(settings.models, tools).plan(payload.message, history)
        _safe_log(memory, session_id, "planner_decision", _decision_payload(decision))
    except (PlannerError, RuntimeError) as exc:
        _safe_log(memory, session_id, "planner_error", {"error": str(exc)})
        reply, source = await _fallback_answer(payload.message, history, settings)
        memory.add_message(session_id, "assistant", reply)
        return ChatResponse(session_id=session_id, reply=reply, source=source)

    if decision.type in {"answer", "done"}:
        reply = decision.final_response
        memory.add_message(session_id, "assistant", reply)
        return ChatResponse(session_id=session_id, reply=reply, source="planner-answer")

    if decision.type == "confirmation_required":
        reply = decision.final_response
        memory.add_message(session_id, "assistant", reply)
        return ChatResponse(session_id=session_id, reply=reply, source="planner-confirmation", requires_confirmation=True, action=decision.action)

    results = executor.execute_all(decision.tool_calls)
    _safe_log(memory, session_id, "tool_results", {"results": _results_payload(results)})
    if any(result.requires_confirmation for result in results):
        pending = next(result for result in results if result.requires_confirmation)
        reply = pending.error or "This action requires confirmation."
        memory.add_message(session_id, "assistant", reply)
        return ChatResponse(session_id=session_id, reply=reply, source="executor-confirmation", requires_confirmation=True, action=pending.action)

    reply, source = await _synthesize_tool_response(payload.message, results, history, settings)
    memory.add_message(session_id, "assistant", reply)
    _safe_log(memory, session_id, "assistant_response", {"source": source, "reply": reply})
    return ChatResponse(session_id=session_id, reply=reply, source=source)


@router.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        session_id = payload.session_id or uuid4().hex
        memory = request.app.state.memory
        settings = request.app.state.settings

        fast = maybe_handle_fast_command(payload.message, tools)
        if fast is not None:
            reply, source = fast
            memory.add_message(session_id, "user", payload.message)
            memory.add_message(session_id, "assistant", reply)
            _safe_log(memory, session_id, "deterministic_command", {"source": source, "reply": reply})
            yield _json_line({"type": "meta", "session_id": session_id, "source": source})
            yield _json_line({"type": "token", "text": reply})
            yield _json_line({"type": "done", "reply": reply})
            return

        if is_agentic_intent(payload.message):
            history = memory.recent_messages(session_id)
            memory.add_message(session_id, "user", payload.message)
            yield _json_line({"type": "meta", "session_id": session_id, "source": "agent-runner", "route": "agentic"})
            yield _json_line({"type": "agent_task", "message": "Agent task started"})
            result = await run_agentic_task(
                payload.message,
                {
                    "settings": settings,
                    "registry": tools,
                    "executor": executor,
                    "memory": memory,
                    "session_id": session_id,
                    "history": history,
                    "execute_tools": True,
                },
            )
            for event in result.get("events", []):
                if event.get("type") == "agent_task":
                    continue
                yield _json_line(event)
            reply = result.get("final_response") or "I stopped the task without a final response."
            memory.add_message(session_id, "assistant", reply)
            _safe_log(memory, session_id, "agent_task_result", {"task_id": result.get("task_id"), "status": result.get("status"), "safety_stops": result.get("safety_stops")})
            if result.get("requires_confirmation"):
                yield _json_line({"type": "confirmation_required", "requires_confirmation": True, "action": result.get("action"), "message": reply})
            yield _json_line({"type": "token", "text": reply})
            yield _json_line({"type": "done", "reply": reply})
            return


        history = memory.recent_messages(session_id)
        memory.add_message(session_id, "user", payload.message)
        yield _json_line({"type": "planning", "message": "Planning..."})

        try:
            decision = await ToolCallPlanner(settings.models, tools).plan(payload.message, history)
            _safe_log(memory, session_id, "planner_decision", _decision_payload(decision))
        except (PlannerError, RuntimeError) as exc:
            _safe_log(memory, session_id, "planner_error", {"error": str(exc)})
            route = select_model(payload.message, settings.models)
            reply_parts: list[str] = []
            yield _json_line({"type": "meta", "session_id": session_id, "source": _source(route), "route": route.reason})
            try:
                async for token in _stream_with_route(payload.message, history, route, settings):
                    reply_parts.append(token)
                    yield _json_line({"type": "token", "text": token})
            except RuntimeError as model_exc:
                fallback = ModelRoute("ollama", settings.models.fast_model, "fallback-local")
                yield _json_line({"type": "meta", "session_id": session_id, "source": _source(fallback), "route": fallback.reason})
                try:
                    async for token in _stream_with_route(payload.message, history, fallback, settings):
                        reply_parts.append(token)
                        yield _json_line({"type": "token", "text": token})
                except RuntimeError:
                    message = f"Planner failed, then model fallback failed too. First error: {model_exc}"
                    memory.add_message(session_id, "assistant", message)
                    yield _json_line({"type": "error", "message": message})
                    return
            reply = "".join(reply_parts).strip() or "I heard you, but the model returned an empty response."
            memory.add_message(session_id, "assistant", reply)
            yield _json_line({"type": "done", "reply": reply})
            return

        yield _json_line({"type": "meta", "session_id": session_id, "source": f"planner:{decision.type}", "route": decision.reason})

        if decision.type in {"answer", "done"}:
            reply = decision.final_response
            memory.add_message(session_id, "assistant", reply)
            yield _json_line({"type": "token", "text": reply})
            yield _json_line({"type": "done", "reply": reply})
            return

        if decision.type == "confirmation_required":
            reply = decision.final_response
            memory.add_message(session_id, "assistant", reply)
            yield _json_line({"type": "confirmation_required", "requires_confirmation": True, "action": decision.action, "message": reply})
            yield _json_line({"type": "token", "text": reply})
            yield _json_line({"type": "done", "reply": reply})
            return

        results = []
        for call in decision.tool_calls:
            yield _json_line({"type": "tool", "tool": call.tool, "args": call.args})
            result = executor.execute(call)
            results.append(result)
            yield _json_line({"type": "tool_result", **result.as_dict()})
            if result.requires_confirmation:
                break

        _safe_log(memory, session_id, "tool_results", {"results": _results_payload(results)})
        if any(result.requires_confirmation for result in results):
            pending = next(result for result in results if result.requires_confirmation)
            reply = pending.error or "This action requires confirmation."
            memory.add_message(session_id, "assistant", reply)
            yield _json_line({"type": "confirmation_required", "requires_confirmation": True, "action": pending.action, "message": reply})
            yield _json_line({"type": "token", "text": reply})
            yield _json_line({"type": "done", "reply": reply})
            return

        reply, source = await _synthesize_tool_response(payload.message, results, history, settings)
        memory.add_message(session_id, "assistant", reply)
        _safe_log(memory, session_id, "assistant_response", {"source": source, "reply": reply})
        yield _json_line({"type": "meta", "session_id": session_id, "source": source})
        yield _json_line({"type": "token", "text": reply})
        yield _json_line({"type": "done", "reply": reply})
 
    return StreamingResponse(stream(), media_type="application/x-ndjson")


@router.get("/screen/snapshot")
async def screen_snapshot(request: Request) -> Response:
    settings = request.app.state.settings
    if not settings.features.screen_capture:
        raise HTTPException(status_code=403, detail="Screen capture is disabled.")
    try:
        image = capture_primary_screen_jpeg()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Screen capture failed: {exc}") from exc
    return Response(content=image, media_type="image/jpeg")





