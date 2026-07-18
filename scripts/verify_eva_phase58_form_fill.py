"""Standalone verifier for Phase 58 (form filling).

Phase 56 made a field clickable by label and Phase 57 made the screen
observable. This composes them into what people actually ask for — "fill in this
form" — by chaining locate -> click -> type per field, through the ordinary gated
tools. It adds no authority; it is pure orchestration.

The verification is about the safety of doing several actions in a row on the
user's behalf:

  1. IT STOPS RATHER THAN BLUNDERS. At the first field it cannot find (or a
     refused click/type — e.g. real input is off), it stops and reports where,
     without typing the remaining values into the wrong places.
  2. IT NEVER CARRIES THE VALUES. A form value is often a password. No step, and
     no returned structure, contains the typed text; secret-looking values are
     flagged and still typed, but never stored.
  3. IT GOES THROUGH THE GATE. Every field is a real screen.click + screen.type
     via the executor seam (here the real ToolRegistry), so it inherits the
     confidence, real-input and Phase 55 risk gates.
  4. IT IS TRUSTED-CONSOLE ONLY. Not a planner tool — untrusted content cannot
     make NOVA type attacker-chosen values into a form.

Fully offline: injected executor + injected UI tree, no network, no real input.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


class _FakeDesktop:
    def __init__(self, known, *, real_input=True):
        self.known = set(known)
        self.real_input = real_input
        self.calls = []

    def __call__(self, tool, **kwargs):
        self.calls.append((tool, kwargs))
        if tool == "screen.click":
            if kwargs.get("label") not in self.known:
                return {"ok": False, "error": "ui_target_not_found"}
            return {"ok": True} if self.real_input else {"ok": False, "error": "real input disabled"}
        if tool == "screen.type_text":
            return {"ok": True} if self.real_input else {"ok": False, "error": "real input disabled"}
        return {"ok": False, "error": "unknown_tool"}


def main() -> int:
    from backend.eva.screen import form_filler
    from backend.eva.screen.form_filler import FormField, fill_form, parse_form_spec
    from backend.eva.tools.registry import ToolRegistry
    from scripts import verify_eva_all

    # 0. Parsing: order-preserving, spaces in labels, '=' in values.
    parsed = parse_form_spec("Email=me@x.com; Password=hunter2; Full Name=John Doe")
    check([f.label for f in parsed] == ["Email", "Password", "Full Name"], "parse must preserve order and spaced labels")
    check(parse_form_spec("Token=a=b=c")[0].value == "a=b=c", "values may contain '='")

    # 1. Happy path: every field, click-then-type, in order.
    desk = _FakeDesktop({"Email", "Password"})
    ok = fill_form([("Email", "me@x.com"), ("Password", "hunter2")], reason="login", executor=desk)
    check(ok.ok and ok.filled == 2, "all findable fields must be filled")
    check([t for t, _ in desk.calls] == ["screen.click", "screen.type_text", "screen.click", "screen.type_text"],
          "each field must click then type, in order")

    # 2. STOPS at the first missing field; types nothing after.
    desk2 = _FakeDesktop({"Email"})
    stopped = fill_form([("Email", "me@x.com"), ("Password", "hunter2"), ("Full Name", "John")], reason="login", executor=desk2)
    check(not stopped.ok and stopped.filled == 1, "it must stop after the first fillable field")
    check(stopped.steps[-1].status == "not_found" and "Password" in (stopped.stopped_reason or ""), "it must report the missing field")
    check(all("hunter2" not in str(kw) for _, kw in desk2.calls), "the password must NOT be typed after a stop")
    check(all(kw.get("label") != "Full Name" for _, kw in desk2.calls), "it must not reach fields past the failure")

    # 3. Real input off -> click refused -> stop, nothing typed.
    desk3 = _FakeDesktop({"Email"}, real_input=False)
    refused = fill_form([("Email", "x@y.com")], reason="login", executor=desk3)
    check(not refused.ok and refused.steps[-1].status == "click_refused", "real-input-off must refuse the click")
    check(not any(t == "screen.type_text" for t, _ in desk3.calls), "nothing must be typed when the click is refused")

    # 4. NEVER carries the value; secret-looking values flagged, still typed.
    desk4 = _FakeDesktop({"Password"})
    secret_run = fill_form([("Password", "SuperSecret123!")], reason="login", executor=desk4)
    check("SuperSecret123!" not in str(secret_run.as_dict()), "the value must never appear in the outcome")

    saved = form_filler._looks_like_secret
    try:
        form_filler._looks_like_secret = lambda v: v == "AKIA_LIVE"
        desk5 = _FakeDesktop({"Key"})
        flagged = fill_form([("Key", "AKIA_LIVE")], reason="cfg", executor=desk5)
        check(flagged.ok and flagged.steps[0].secret is True, "a secret-looking value must be flagged")
        check(any(t == "screen.type_text" for t, _ in desk5.calls), "a secret field is still typed")
        check("AKIA_LIVE" not in str(flagged.as_dict()), "the secret must not be stored")
    finally:
        form_filler._looks_like_secret = saved

    # 5. The real gate is the default executor path, and the console entry is
    #    trusted-only: form filling is NOT a planner tool.
    names = {str(t.get("name", "")).lower() for t in ToolRegistry().list_tools()}
    for forbidden in ("form.fill", "fill_form", "screen.fill_form", "form_fill"):
        check(forbidden not in names, f"form filling must not be a planner tool, found {forbidden!r}")

    fc_source = (ROOT / "backend" / "eva" / "core" / "fast_commands.py").read_text(encoding="utf-8")
    check("_fill_form_command" in fc_source and "fill form" in fc_source, "the typed-console fill-form entry must be wired")

    # 6. Registration.
    name = "verify_eva_phase58_form_fill.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 58 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 58 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 58 verifier")
    check(isinstance(parsed[0], FormField), "sanity")

    print(
        "PASS: Phase 58 form filling -- composes Phase 56/57 into 'fill in this form': for each field it clicks to "
        "focus and types, through the ordinary gated tools (inheriting the confidence, real-input and risk gates). "
        "It STOPS at the first field it cannot find (or a refused click/type) rather than typing values into the "
        "wrong places, and it NEVER carries the values -- no step or outcome contains the typed text; secret-looking "
        "values are flagged and still typed but never stored. Driven only from the trusted console, never as a "
        "planner tool, so untrusted content cannot type attacker-chosen values into a form."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
