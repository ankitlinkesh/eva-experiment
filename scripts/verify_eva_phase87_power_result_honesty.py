"""Standalone verifier for Phase 87 (string-result honesty in the approval handoff).

Sweeping the remaining gated tools through approval surfaced this: `system_power`
and `guarded_power_action` (and the media tools) return a human-readable STRING,
not a dict. The confirm/override handoff decided success with
`isinstance(executed, dict) and executed.get("ok")`, so a string result fell
into the failure branch -- an approved power action the user explicitly
override-approved was reported as "execution did not complete." even when it
ran. Same honest-effects family as capture_screen (Phase 86), for string tools.

The post-approval rendering is now a pure helper, `_render_executed`:
  1. A non-dict (string) result is a SUCCESS and its text is surfaced.
  2. A dict with ok:True is success (Phase 85 output allowlist unchanged).
  3. A dict WITHOUT ok:True is STILL a failure -- the fix must not loosen
     failure detection (run_approved, Phase 86, wraps genuine crashes as ok:False).

Fully offline: pure string rendering, no ledger, no registry, and -- importantly
-- NO power action is ever executed (the string is a fixture, not a real call).
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
    from eva.permissions.confirmation import _render_executed

    base = "Confirmed pending action `act_x`."

    # ------------------------------------------------------------------ 1
    string_out = _render_executed("act_x", base, "Locking the laptop.")
    check("did not complete" not in string_out.lower(), "a string result (e.g. system_power) was reported as not completing")
    check("Locking the laptop." in string_out, "a string result's text was not surfaced")
    none_out = _render_executed("act_x", base, None)
    check("did not complete" not in none_out.lower() and "successfully" in none_out.lower(), "a None result was not a plain success")

    # ------------------------------------------------------------------ 2
    check("successfully" in _render_executed("act_x", base, {"ok": True}).lower(), "dict ok:True stopped being a success")
    check("hello" in _render_executed("act_x", base, {"ok": True, "text": "hello"}), "dict ok:True lost its output")

    # ------------------------------------------------------------------ 3 (must NOT loosen failure detection)
    fail = _render_executed("act_x", base, {"ok": False, "error": "boom"})
    check("did not complete" in fail.lower() and "boom" in fail, "a real failure dict was no longer reported as a failure")
    check("did not complete" in _render_executed("act_x", base, {"error": "no ok"}).lower(), "a dict without ok was wrongly treated as success")

    # ------------------------------------------------------------------ registration
    import verify_eva_all

    name = "verify_eva_phase87_power_result_honesty.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 87 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 87 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 87 verifier")

    print(
        "PASS: Phase 87 string-result honesty. system_power/guarded_power_action (and media tools) return a "
        "human-readable string, not a dict, so the approval handoff -- which decided success via isinstance(dict) and "
        "ok -- reported an approved, executed power action as 'execution did not complete'. The rendering is now a pure "
        "_render_executed helper: a non-dict (string) result is a success and its text is surfaced; dict ok:True is "
        "success with the Phase 85 output allowlist; and a dict without ok:True is STILL a failure, so the fix does not "
        "loosen failure detection (a real ok:False, including run_approved's Phase 86 graceful wrap, stays a failure). "
        "No power action is executed to prove any of this."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
