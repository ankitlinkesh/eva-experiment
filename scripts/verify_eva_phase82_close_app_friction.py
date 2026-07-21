"""Standalone verifier for Phase 82 (close_app friction).

close_app was allow-class -- it auto-ran with zero friction, exactly like
open_app -- even though closing an app can DISCARD UNSAVED WORK. Its
`safety_level="sensitive"` did nothing (the gate reads only "dangerous"/"safe"),
and the SYSTEM_CHANGE action_type of the deleted `app.close_request` was never
carried over (a gap the source itself flagged near message.prepare). It now asks
first, matching screen.submit_form (also SAFE_LOCAL_UI, confirm-class because it
can commit or lose data).

What this verifies:

  1. close_app is CONFIRM-class -- it no longer auto-runs -- while open_app
     stays allow (opening is harmless; the change is specific to closing).
  2. Calling it returns a pending confirmation, not an execution.
  3. A non-allowlisted app is refused BEFORE the gate, so a close that could
     only ever be rejected is not asked to be confirmed first (the Phase 74
     lesson). An allowlisted close reaches the confirmation.
  4. The console renders the confirmation message, not a raw dict.

Fully offline: no real process is closed; the one close that survives the
allowlist stops at the gate.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from eva.core.fast_commands import maybe_handle_fast_command
    from eva.core.fast_command_formatters import _run_tool
    from eva.security.tool_gate import classify_tool_call
    from eva.tools.desktop import is_closeable
    from eva.tools.registry import ToolRegistry

    registry = ToolRegistry()

    # ------------------------------------------------------------------ 1
    check(classify_tool_call(registry.get("close_app")) == "confirm", "close_app is not confirm-class -- it still auto-runs")
    check(classify_tool_call(registry.get("open_app")) == "allow", "open_app should stay allow-class (opening is harmless)")

    # ------------------------------------------------------------------ 2
    result = registry.run("close_app", app_name="notepad")
    check(isinstance(result, dict) and result.get("requires_confirmation") is True, "close_app executed instead of asking for confirmation")
    check(result.get("risk_class") == "confirm", "close_app's pending action is not confirm-class")

    # ------------------------------------------------------------------ 3
    check(is_closeable("chrome") and is_closeable("notepad"), "an allowlisted app was reported non-closeable")
    check(not is_closeable("unknownapp"), "an unknown app was reported closeable")
    check(not is_closeable("system process"), "a system process was reported closeable")

    allowed = maybe_handle_fast_command("close chrome", registry, {})
    check(allowed is not None, "the console did not handle `close chrome`")
    low = allowed[0].lower()
    check("approve" in low or "confirm" in low, "an allowlisted close did not ask for confirmation")

    refused = maybe_handle_fast_command("close unknownapp", registry, {})
    check(refused is not None, "the console did not handle `close unknownapp`")
    check("safe close allowlist" in refused[0].lower(), "an unknown app was not refused with the allowlist message")
    check("approve" not in refused[0].lower(), "an unknown app was asked to be confirmed before being refused (parked at the gate -- Phase 74 lesson)")

    # ------------------------------------------------------------------ 4
    text, _ = _run_tool(registry, "close_app", {}, app_name="chrome")
    check(not text.strip().startswith("{"), "the console rendered the raw pending dict instead of the confirmation message")
    check("approve" in text.lower() or "confirm" in text.lower(), "the rendered close confirmation lost its message")

    # ------------------------------------------------------------------ registration
    import verify_eva_all

    name = "verify_eva_phase82_close_app_friction.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 82 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 82 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 82 verifier")

    print(
        "PASS: Phase 82 close_app friction. close_app was allow-class -- it auto-ran with zero friction, like open_app "
        "-- even though closing an app can discard unsaved work; safety_level='sensitive' did nothing at the gate and "
        "the deleted app.close_request's SYSTEM_CHANGE type was never carried over. It is now confirm-class (asks "
        "first, matching screen.submit_form) while open_app stays allow. A non-allowlisted or system app is refused "
        "before the gate, so a close that could only be rejected is not confirmed first (the Phase 74 lesson); only an "
        "allowlisted close reaches the confirmation, and the console renders that confirmation rather than a raw dict."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
