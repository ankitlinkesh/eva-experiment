"""Executable spec for string-result honesty in the approval handoff (Phase 87).

Found by sweeping the remaining gated tools: `system_power` (and the media
tools) return a human-readable STRING, not a dict. The confirm/override handoff
decided success with `isinstance(executed, dict) and executed.get("ok")`, so a
string result fell straight into the failure branch -- an approved power action
(a shutdown/lock/restart the user explicitly override-approved) was reported as
"execution did not complete." even when it ran. Same "honest effects" family as
the capture_screen bug (Phase 86), for string-returning tools.

The rendering is now a pure helper, `_render_executed`, so every branch is
directly testable:
  * a non-dict (string) result is a SUCCESS and its text is surfaced;
  * a dict with ok:True is success (with the Phase 85 output allowlist);
  * a dict WITHOUT ok:True is still a real failure -- the fix must not loosen
    failure detection (run_approved, Phase 86, wraps genuine crashes as ok:False).
"""

from __future__ import annotations

from eva.permissions.confirmation import _render_executed

BASE = "Confirmed pending action `act_x`."


class TestStringResultIsSuccess:
    def test_a_string_result_is_not_reported_as_did_not_complete(self) -> None:
        out = _render_executed("act_x", BASE, "Locking the laptop.")
        assert "did not complete" not in out.lower()
        assert "Locking the laptop." in out

    def test_none_result_is_a_plain_success(self) -> None:
        out = _render_executed("act_x", BASE, None)
        assert "did not complete" not in out.lower()
        assert "successfully" in out.lower()


class TestDictResultsAreUnchanged:
    def test_ok_true_is_success(self) -> None:
        assert "successfully" in _render_executed("act_x", BASE, {"ok": True}).lower()

    def test_ok_true_with_output_surfaces_it(self) -> None:
        assert "hello" in _render_executed("act_x", BASE, {"ok": True, "text": "hello"})

    def test_a_real_failure_dict_still_reports_failure(self) -> None:
        """The fix must NOT turn genuine failures into success. A dict without
        ok:True (e.g. run_approved's graceful ok:False from Phase 86) stays a
        failure."""
        out = _render_executed("act_x", BASE, {"ok": False, "error": "boom"})
        assert "did not complete" in out.lower()
        assert "boom" in out

    def test_ok_missing_is_treated_as_failure_for_a_dict(self) -> None:
        # A dict that does not claim ok is not asserted successful (only strings
        # -- which cannot carry an ok flag -- get the benefit of the doubt).
        out = _render_executed("act_x", BASE, {"error": "no ok key"})
        assert "did not complete" in out.lower()
