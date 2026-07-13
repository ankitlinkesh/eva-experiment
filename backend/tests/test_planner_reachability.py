"""Planner reachability of web.* and mcp.* tools.

ToolRegistry.planner_specs() returns the fixed list of planner-visible tool
specs that the LLM planner is allowed to choose from. `web.*` (Playwright DOM
tools) and `mcp.*` (MCP server tools) always exist in `self._tools` (when
applicable), but must only be surfaced to the planner when they are actually
usable:

  * web.*  -- only when EVA_V2_PLAYWRIGHT_ENABLED is truthy.
  * mcp.*  -- only when the MCP subsystem has actually loaded specs into the
              module-level `_MCP_TOOL_SPECS` cache (merged into every fresh
              ToolRegistry's `self._tools` in __init__).

`screen.*` (desktop mouse/keyboard) must never be planner-reachable -- that is
a deliberate safety choice, endpoint-only, regardless of any flag.

With both the flag off and no MCP tools loaded (today's default environment),
planner_specs() must be byte-identical to before this change: no web./mcp.
names, screen. names never present, and the pre-existing fixed-list tools
(e.g. "web_search", the underscore-named legacy tool) still present.
"""

from __future__ import annotations

import pytest

from backend.eva.tools.registry import _MCP_TOOL_SPECS


@pytest.fixture(autouse=True)
def _clear_mcp_tool_specs_cache():
    """Prevent this file's injected mcp.ex.echo spec from leaking into other
    test files/modules via the shared module-level _MCP_TOOL_SPECS cache."""
    _MCP_TOOL_SPECS.clear()
    try:
        yield
    finally:
        _MCP_TOOL_SPECS.clear()


def test_default_environment_has_no_web_mcp_or_screen_tools():
    """Flag off, no MCP loaded: planner surface is unchanged from today."""
    from backend.eva.tools.registry import ToolRegistry

    registry = ToolRegistry()
    names = {spec["name"] for spec in registry.planner_specs()}

    assert not any(name.startswith("web.") for name in names), (
        f"web.* tools must not be planner-reachable by default: {sorted(n for n in names if n.startswith('web.'))}"
    )
    assert not any(name.startswith("mcp.") for name in names), (
        f"mcp.* tools must not be planner-reachable when none are loaded: {sorted(n for n in names if n.startswith('mcp.'))}"
    )
    assert not any(name.startswith("screen.") for name in names), (
        f"screen.* tools must never be planner-reachable: {sorted(n for n in names if n.startswith('screen.'))}"
    )

    # Prove the base fixed list is intact -- a known pre-existing tool is
    # still present.
    assert "web_search" in names


def test_web_tools_reachable_when_playwright_enabled(monkeypatch):
    monkeypatch.setenv("EVA_V2_PLAYWRIGHT_ENABLED", "1")
    from backend.eva.tools.registry import ToolRegistry

    registry = ToolRegistry()
    names = {spec["name"] for spec in registry.planner_specs()}

    for expected in ("web.open_url", "web.click", "web.type"):
        assert expected in names, f"{expected} should be planner-reachable when Playwright is enabled: {sorted(names)}"

    assert not any(name.startswith("screen.") for name in names), (
        "screen.* tools must stay endpoint-only even when Playwright is enabled"
    )


def test_mcp_tools_reachable_when_loaded():
    from backend.eva.tools.registry import ToolRegistry, ToolSpec, register_mcp_tool_specs

    spec = ToolSpec(
        name="mcp.ex.echo",
        description="Echo test MCP tool.",
        args_schema={"type": "object", "properties": {}, "required": []},
        safety_level="sensitive",
        handler=lambda **_kwargs: {"ok": True},
        action_type="MCP_TOOL_CALL",
        risk_categories=("MCP_TOOL_CALL",),
        requires_confirmation=True,
    )
    register_mcp_tool_specs({"mcp.ex.echo": spec})

    registry = ToolRegistry()
    names = {s["name"] for s in registry.planner_specs()}

    assert "mcp.ex.echo" in names, f"mcp.ex.echo should be planner-reachable once loaded: {sorted(names)}"
