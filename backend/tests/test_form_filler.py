"""Form filling — locate -> click -> type, safely (Phase 58).

The orchestration is tested with an injected executor (no real desktop). The
properties that matter are safety ones: it stops rather than blundering, and it
never carries the field values.
"""

from __future__ import annotations

import pytest

from eva.screen.form_filler import FormField, fill_form, parse_form_spec


class FakeDesktop:
    """A stand-in gate: known labels click/type OK; unknown labels are not found."""

    def __init__(self, known, *, real_input=True):
        self.known = set(known)
        self.real_input = real_input
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, tool, **kwargs):
        self.calls.append((tool, kwargs))
        if tool == "screen.click":
            if kwargs.get("label") not in self.known:
                return {"ok": False, "error": "ui_target_not_found"}
            if not self.real_input:
                return {"ok": False, "error": "real input disabled"}
            return {"ok": True}
        if tool == "screen.type_text":
            if not self.real_input:
                return {"ok": False, "error": "real input disabled"}
            return {"ok": True}
        return {"ok": False, "error": "unknown_tool"}


# -- parsing ----------------------------------------------------------------

def test_parse_preserves_order_and_spaces_in_labels():
    fields = parse_form_spec("Email=me@x.com; Password=hunter2; Full Name=John Doe")
    assert [f.label for f in fields] == ["Email", "Password", "Full Name"]
    assert fields[0].value == "me@x.com"


def test_parse_keeps_equals_in_values():
    fields = parse_form_spec("Token=a=b=c")
    assert fields[0].value == "a=b=c"


def test_parse_skips_clauses_without_equals():
    assert parse_form_spec("just some text; Email=x@y.com") == [FormField("Email", "x@y.com")]


# -- the happy path ---------------------------------------------------------

def test_fills_every_field_in_order():
    desk = FakeDesktop({"Email", "Password", "Submit"})
    outcome = fill_form(
        [("Email", "me@x.com"), ("Password", "hunter2")],
        reason="login", executor=desk,
    )
    assert outcome.ok is True
    assert outcome.filled == 2
    assert [s.status for s in outcome.steps] == ["filled", "filled"]
    # click then type, per field, in order
    tools = [c[0] for c in desk.calls]
    assert tools == ["screen.click", "screen.type_text", "screen.click", "screen.type_text"]


# -- it STOPS rather than blundering ---------------------------------------

def test_stops_at_the_first_missing_field():
    desk = FakeDesktop({"Email"})  # Password field does not exist
    outcome = fill_form(
        [("Email", "me@x.com"), ("Password", "hunter2"), ("Full Name", "John")],
        reason="login", executor=desk,
    )
    assert outcome.ok is False
    assert outcome.filled == 1
    assert outcome.steps[-1].status == "not_found"
    assert "Password" in outcome.stopped_reason
    # It must NOT have tried to type the password or touch Full Name.
    assert ("screen.type_text", {"reason": "login", "text": "hunter2"}) not in desk.calls
    assert all(c[1].get("label") != "Full Name" for c in desk.calls)


def test_real_input_off_stops_without_typing():
    desk = FakeDesktop({"Email"}, real_input=False)
    outcome = fill_form([("Email", "me@x.com")], reason="login", executor=desk)
    assert outcome.ok is False
    assert outcome.steps[-1].status == "click_refused"
    assert not any(c[0] == "screen.type_text" for c in desk.calls)


# -- it never carries the values -------------------------------------------

def test_steps_never_contain_the_value():
    desk = FakeDesktop({"Password"})
    outcome = fill_form([("Password", "SuperSecret123!")], reason="login", executor=desk)
    blob = str(outcome.as_dict())
    assert "SuperSecret123!" not in blob


def test_secret_looking_values_are_flagged_but_still_typed(monkeypatch):
    import eva.screen.form_filler as ff

    monkeypatch.setattr(ff, "_looks_like_secret", lambda v: v == "AKIA_LIVE_SECRET")
    desk = FakeDesktop({"Key"})
    outcome = fill_form([("Key", "AKIA_LIVE_SECRET")], reason="config", executor=desk)
    assert outcome.ok is True
    assert outcome.steps[0].secret is True
    # ...and still typed (the point of a secret field), but not stored:
    assert any(c[0] == "screen.type_text" for c in desk.calls)
    assert "AKIA_LIVE_SECRET" not in str(outcome.as_dict())


# -- the console entry is trusted-only -------------------------------------

def test_fill_form_is_not_a_planner_tool():
    from eva.tools.registry import ToolRegistry

    names = {str(t.get("name", "")).lower() for t in ToolRegistry().list_tools()}
    for forbidden in ("form.fill", "fill_form", "screen.fill_form"):
        assert forbidden not in names
