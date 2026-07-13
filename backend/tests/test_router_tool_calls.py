"""The router must accept a planner response that has tool_calls but empty text.

Native function-calling returns a tool call with no text content. The router
historically accepted a planner response only when response.text was non-empty
(and rejected non-JSON text), which silently dropped native tool calls. These
tests lock the fix: a tool-call-only response is treated as usable, not as a
retryable/invalid failure. (End-to-end native calling is proven live against
the real Gemini API; this is the fast regression guard.)
"""
from __future__ import annotations

from backend.eva.llm.router import _is_retryable_failure
from backend.eva.llm.types import LLMResponse


def _tool_call_response() -> LLMResponse:
    return LLMResponse(
        provider="gemini",
        model="gemini-2.5-flash",
        text="",
        ok=True,
        status_code=200,
        tool_calls=[{"id": "call_0", "type": "function", "function": {"name": "web_search", "arguments": "{\"query\": \"cats\"}"}}],
    )


def test_tool_call_only_response_is_not_a_retryable_failure():
    # ok + tool_calls (empty text) must count as a usable success, not a retry.
    assert _is_retryable_failure(_tool_call_response()) is False


def test_plain_text_response_still_not_retryable():
    # Regression guard: the text path is unchanged by the tool_calls addition.
    r = LLMResponse(provider="gemini", model="m", text="hello", ok=True, status_code=200)
    assert _is_retryable_failure(r) is False
