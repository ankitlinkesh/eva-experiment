"""Tests for the Phase 40c MCP trust model.

Two controls: a trust allowlist (env or per-server config) gating which
servers' tools ever get registered, and a per-server call budget bounding how
many times a trusted server can be invoked per process. Backward compatible:
with no policy configured at all, every server is trusted (today's behavior).
"""

from __future__ import annotations

import json

import pytest

from backend.eva.mcp import trust
from backend.eva.mcp.config import McpServerConfig, load_mcp_config


@pytest.fixture(autouse=True)
def _reset_budgets():
    trust.reset_budgets()
    yield
    trust.reset_budgets()


def _server(name: str, trusted: bool = False) -> McpServerConfig:
    return McpServerConfig(name=name, transport="stdio", trusted=trusted)


def test_no_policy_configured_trusts_everything(monkeypatch):
    monkeypatch.delenv("EVA_MCP_TRUSTED_SERVERS", raising=False)
    a = _server("a")
    b = _server("b")

    assert trust.trust_configured([a, b]) is False
    kept = trust.filter_trusted([a, b])
    assert {s.name for s in kept} == {"a", "b"}


def test_marked_trusted_server_filters_out_unmarked(monkeypatch):
    monkeypatch.delenv("EVA_MCP_TRUSTED_SERVERS", raising=False)
    pinned = _server("pinned", trusted=True)
    untrusted = _server("untrusted", trusted=False)

    assert trust.trust_configured([pinned, untrusted]) is True
    kept = trust.filter_trusted([pinned, untrusted])
    assert [s.name for s in kept] == ["pinned"]


def test_allowlist_env_filters_to_named_server(monkeypatch):
    monkeypatch.setenv("EVA_MCP_TRUSTED_SERVERS", "pinned")
    pinned = _server("pinned")
    other = _server("other")

    kept = trust.filter_trusted([pinned, other])
    assert [s.name for s in kept] == ["pinned"]


def test_server_budget_exceeded_after_n_calls(monkeypatch):
    monkeypatch.setenv("EVA_MCP_SERVER_BUDGET", "2")

    assert trust.budget_exceeded("s") is False
    trust.record_call("s")
    assert trust.budget_exceeded("s") is False
    trust.record_call("s")
    assert trust.budget_exceeded("s") is True


def test_config_parses_trusted_field(monkeypatch, tmp_path):
    config_path = tmp_path / "mcp_servers.json"
    config_path.write_text(
        json.dumps(
            {
                "servers": [
                    {"name": "pinned", "transport": "stdio", "command": "run-pinned", "trusted": True},
                    {"name": "unpinned", "transport": "stdio", "command": "run-unpinned"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("EVA_MCP_CONFIG_PATH", str(config_path))

    servers = load_mcp_config()
    by_name = {s.name: s for s in servers}

    assert by_name["pinned"].trusted is True
    assert by_name["unpinned"].trusted is False
