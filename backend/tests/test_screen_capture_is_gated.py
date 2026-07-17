"""Screen capture must be gated — regression found by real workflow probing.

`capture_screen` and `analyze_screen` grab the whole screen and write a PNG to
disk. They carried no explicit action_type, so they defaulted to
SAFE_LOCAL_READ, which made them ALLOW-class: they ran immediately, with no
confirmation. The gate was inverted — the properly gated `screen.observe` was
NOT planner-reachable, while these two were.

Worse, the Phase 40 injection defense only escalates *privileged* tools
(`_is_privileged_tool`, i.e. confirm/override/hard_block). An allow-class screen
grab was invisible to it, so injected web content could steer the planner into
screenshotting the user with no confirmation and no escalation.

Taking a picture of your screen is a PRIVACY_SCREEN_READ. These tests pin that.
"""

from __future__ import annotations

import pytest

from eva.agent.runner import _is_privileged_tool
from eva.security import tool_gate
from eva.tools.registry import ToolRegistry

SCREEN_CAPTURE_TOOLS = ("capture_screen", "analyze_screen", "screen.observe")


@pytest.fixture()
def registry():
    tool_gate.reset_pending_calls()
    yield ToolRegistry()
    tool_gate.reset_pending_calls()


@pytest.mark.parametrize("tool", SCREEN_CAPTURE_TOOLS)
def test_every_pixel_grabbing_tool_is_override_class(registry, tool):
    spec = registry.get(tool)
    assert spec is not None, f"{tool} must be registered"
    assert spec.action_type == "PRIVACY_SCREEN_READ", f"{tool} grabs pixels; that is a privacy read, not a safe local read"
    assert tool_gate.classify_tool_call(spec) == "override", f"{tool} must be override-class"


@pytest.mark.parametrize("tool", SCREEN_CAPTURE_TOOLS)
def test_screen_capture_is_covered_by_the_injection_defense(registry, tool):
    """Phase 40 only escalates privileged tools. If a screen grab isn't
    privileged, injected content can steer the planner into it unchecked."""
    assert _is_privileged_tool(registry, tool) is True, f"{tool} must be privileged so taint-tracking escalates it"


def test_capture_screen_does_not_execute_without_confirmation(registry):
    """The load-bearing check: asking for a screenshot must return a pending
    descriptor, not a screenshot."""
    result = registry.run("capture_screen")
    assert isinstance(result, dict)
    assert result.get("requires_confirmation") is True
    assert result.get("risk_class") == "override"


def test_analyze_screen_does_not_execute_without_confirmation(registry):
    result = registry.run("analyze_screen", question="what is on my screen?")
    assert isinstance(result, dict)
    assert result.get("requires_confirmation") is True


def test_self_approval_cannot_unlock_a_screen_grab(registry):
    """A model-supplied confirmed/_approved argument must carry no authority."""
    result = registry.run("capture_screen", confirmed=True, _approved=True)
    assert isinstance(result, dict)
    assert result.get("requires_confirmation") is True, "self-approval must never unlock a screen capture"


def test_desktop_observe_is_allow_class_metadata_only(registry):
    """desktop_observe is allow-class, so it must have NO pixel path at all.

    It used to accept include_screen + explicit_screen_intent and capture the
    screen when both were true. The gate classifies by tool, not by args, so
    that rode through as allow-class "safe" — and explicit_screen_intent was
    supplied by the CALLER, meaning the LLM authorized its own screen capture.
    Same self-approval bug the `confirmed` argument once had.
    """
    spec = registry.get("desktop_observe")
    assert tool_gate.classify_tool_call(spec) == "allow"
    props = set((spec.args_schema or {}).get("properties") or {})
    assert "include_screen" not in props, "an allow-class tool must not expose a screen-capture switch"
    assert "explicit_screen_intent" not in props, "a caller-supplied flag must never unlock screen capture"
    assert props == {"include_windows"}, f"desktop_observe must be metadata-only, got args {props}"


def test_desktop_observe_returns_metadata_without_a_screenshot(registry):
    result = registry.run("desktop_observe", include_windows=True)
    assert isinstance(result, dict) and result.get("ok")
    assert not result.get("screen_path"), "a metadata observation must never carry a screenshot"


def test_desktop_observe_cannot_be_talked_into_capturing(registry):
    """The old bypass must be impossible, not merely discouraged."""
    with pytest.raises(TypeError):
        registry.run("desktop_observe", include_screen=True, explicit_screen_intent=True)
