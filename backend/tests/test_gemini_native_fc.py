"""Tests for native function-calling (tool-calling) plumbing in GeminiProvider.

Covers:
  * GeminiProvider._sanitize_gemini_schema -- strips unsupported JSON-Schema
    keys and drops empty `required` lists.
  * GeminiProvider._to_gemini_tools -- converts OpenAI-shaped tool specs into
    Gemini's function_declarations shape, omitting `parameters` when the
    schema has no properties.
  * GeminiProvider.complete parsing a functionCall part out of the response
    into LLMResponse.tool_calls (OpenAI shape) when `tools` is passed.
  * Backward compatibility: calling complete() with no `tools` arg is
    byte-identical to today (no "tools"/"toolConfig" keys in the payload,
    tool_calls is None on the response).
"""

from __future__ import annotations

import asyncio
import json

import pytest

from backend.eva.core.config import ModelSettings
from backend.eva.llm.providers.gemini import GeminiProvider


@pytest.fixture(autouse=True)
def _neutralize_rate_limiter(monkeypatch):
    # Isolate these tests from the shared persistent rate-limiter state so real
    # prior usage (e.g. live API calls) cannot make a mocked test flake.
    from backend.eva.llm import rate_limiter

    monkeypatch.setattr(rate_limiter.LLMRateLimiter, "can_call", lambda self, *a, **k: (True, "ok"))
    monkeypatch.setattr(rate_limiter.LLMRateLimiter, "record_success", lambda self, *a, **k: None)
    monkeypatch.setattr(rate_limiter.LLMRateLimiter, "record_failure", lambda self, *a, **k: None)


def test_sanitize_gemini_schema_strips_unsupported_keys():
    provider = GeminiProvider(ModelSettings())
    schema = {
        "type": "object",
        "title": "MySchema",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "additionalProperties": False,
        "properties": {
            "query": {"type": "string", "default": "x", "examples": ["a"]},
        },
        "required": [],
    }

    result = provider._sanitize_gemini_schema(schema)

    assert result["type"] == "object"
    assert "title" not in result
    assert "$schema" not in result
    assert "additionalProperties" not in result
    assert "required" not in result
    assert result["properties"]["query"] == {"type": "string"}


def test_to_gemini_tools_omits_parameters_when_properties_empty():
    provider = GeminiProvider(ModelSettings())
    tools = [
        {
            "type": "function",
            "function": {
                "name": "no_args_tool",
                "description": "Takes no args",
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            },
        }
    ]

    result = provider._to_gemini_tools(tools)

    assert result == [{"function_declarations": [{"name": "no_args_tool", "description": "Takes no args"}]}]


def test_to_gemini_tools_includes_sanitized_parameters_when_present():
    provider = GeminiProvider(ModelSettings())
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "search",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        }
    ]

    result = provider._to_gemini_tools(tools)

    assert len(result) == 1
    decls = result[0]["function_declarations"]
    assert len(decls) == 1
    decl = decls[0]
    assert decl["name"] == "web_search"
    assert decl["description"] == "search"
    assert "parameters" in decl
    assert "additionalProperties" not in decl["parameters"]
    assert decl["parameters"]["properties"] == {"query": {"type": "string"}}
    assert decl["parameters"]["required"] == ["query"]


class _FakeResponse:
    def __init__(self, payload: dict):
        self.status_code = 200
        self.headers: dict[str, str] = {}
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class _FakeAsyncClient:
    """Fake replacement for httpx.AsyncClient used to intercept .post(...)."""

    captured_payloads: list[dict] = []
    response_payload: dict = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        type(self).captured_payloads.append(json)
        return _FakeResponse(type(self).response_payload)


@pytest.fixture(autouse=True)
def _reset_fake_client():
    _FakeAsyncClient.captured_payloads = []
    _FakeAsyncClient.response_payload = {}
    yield
    _FakeAsyncClient.captured_payloads = []
    _FakeAsyncClient.response_payload = {}


@pytest.fixture
def gemini_provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza" + "x" * 35)
    return GeminiProvider(ModelSettings())


def test_complete_with_tools_parses_function_call(monkeypatch, gemini_provider):
    from backend.eva.llm.providers import gemini as gemini_module

    monkeypatch.setattr(gemini_module.httpx, "AsyncClient", _FakeAsyncClient)

    _FakeAsyncClient.response_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"functionCall": {"name": "web_search", "args": {"query": "cats"}}}
                    ]
                }
            }
        ]
    }

    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "search",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        }
    ]

    response = asyncio.run(
        gemini_provider.complete([{"role": "user", "content": "search cats"}], tools=tools)
    )

    assert response.ok is True
    assert response.tool_calls is not None
    assert response.tool_calls[0]["function"]["name"] == "web_search"
    assert json.loads(response.tool_calls[0]["function"]["arguments"]) == {"query": "cats"}

    assert len(_FakeAsyncClient.captured_payloads) == 1
    payload = _FakeAsyncClient.captured_payloads[0]
    assert "tools" in payload
    decls = payload["tools"][0]["function_declarations"]
    assert decls[0]["name"] == "web_search"
    assert "additionalProperties" not in decls[0]["parameters"]


def test_complete_without_tools_is_backward_compatible(monkeypatch, gemini_provider):
    from backend.eva.llm.providers import gemini as gemini_module

    monkeypatch.setattr(gemini_module.httpx, "AsyncClient", _FakeAsyncClient)

    _FakeAsyncClient.response_payload = {
        "candidates": [{"content": {"parts": [{"text": "hi"}]}}]
    }

    response = asyncio.run(gemini_provider.complete([{"role": "user", "content": "hi"}]))

    assert response.ok is True
    assert response.text == "hi"
    assert response.tool_calls is None

    assert len(_FakeAsyncClient.captured_payloads) == 1
    payload = _FakeAsyncClient.captured_payloads[0]
    assert "tools" not in payload
    assert "toolConfig" not in payload
