"""Executable spec for close_app friction (Phase 82).

close_app was allow-class -- it ran with zero friction, exactly like open_app --
even though closing an app can DISCARD UNSAVED WORK. `safety_level="sensitive"`
did nothing (the gate reads only "dangerous"/"safe"), and the SYSTEM_CHANGE
action_type of the deleted `app.close_request` was never carried over. It now
asks first, matching screen.submit_form (also SAFE_LOCAL_UI, confirm-class
because it can commit/lose data).

Two properties:
  1. close_app is confirm-class -- it no longer auto-runs.
  2. A non-allowlisted app is refused BEFORE the gate, so it is not confirmed
     only to be rejected on execution (the Phase 74 lesson). Only an allowlisted
     close reaches the confirmation.
"""

from __future__ import annotations

from eva.tools.desktop import is_closeable
from eva.tools.registry import ToolRegistry
from eva.security.tool_gate import classify_tool_call


class TestCloseAppIsConfirmClass:
    def test_close_app_is_no_longer_allow(self) -> None:
        spec = ToolRegistry().get("close_app")
        assert classify_tool_call(spec) == "confirm"

    def test_open_app_stays_allow_for_contrast(self) -> None:
        """Opening is harmless; the change is specific to closing."""
        assert classify_tool_call(ToolRegistry().get("open_app")) == "allow"

    def test_close_app_does_not_execute_without_confirmation(self) -> None:
        result = ToolRegistry().run("close_app", app_name="notepad")
        assert isinstance(result, dict)
        assert result.get("requires_confirmation") is True
        assert result.get("risk_class") == "confirm"


class TestIsCloseablePredicate:
    def test_allowlisted_apps_are_closeable(self) -> None:
        assert is_closeable("chrome") is True
        assert is_closeable("notepad") is True

    def test_unknown_and_system_apps_are_not_closeable(self) -> None:
        assert is_closeable("unknownapp") is False
        assert is_closeable("system process") is False
        assert is_closeable("") is False


class TestConsoleClosePath:
    def _fast(self, message: str):
        from eva.core.fast_commands import maybe_handle_fast_command

        return maybe_handle_fast_command(message, ToolRegistry(), {})

    def test_allowlisted_close_asks_for_confirmation(self) -> None:
        out = self._fast("close chrome")
        assert out is not None
        text = out[0].lower()
        # The gate's approval prompt, not an executed close.
        assert "approve" in text or "confirm" in text
        assert "close_app(app_name='chrome')" in out[0]

    def test_unknown_close_is_refused_before_the_gate(self) -> None:
        out = self._fast("close unknownapp")
        assert out is not None
        # Immediate allowlist refusal -- never asked to confirm something that
        # would be rejected anyway.
        assert "safe close allowlist" in out[0].lower()
        assert "approve" not in out[0].lower()


class TestRunToolSurfacesConfirmation:
    def test_confirm_result_renders_its_message(self) -> None:
        """A dict with requires_confirmation must render its message, not the
        raw dict repr."""
        from eva.core.fast_command_formatters import _run_tool

        text, _ = _run_tool(ToolRegistry(), "close_app", {}, app_name="chrome")
        assert "{" not in text[:1]  # not a raw dict
        assert "approve" in text.lower() or "confirm" in text.lower()
