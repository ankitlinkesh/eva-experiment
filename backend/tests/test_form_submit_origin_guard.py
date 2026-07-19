"""The origin-binding guard -- the identity half of the phishing gap (Phase 67).

Phase 63's window guard answers "is this still the window I staged against";
it cannot answer "is this still the right SITE", because a phishing page can
simply be titled and styled to look exactly like the real thing while living
at a different domain. This closes that gap by reading the domain from the
browser's own address bar (Chrome/Edge expose it as an Edit control in the
same accessibility tree grounding already walks) and re-checking it before
every field and before the final submit, exactly mirroring how the window
guard re-checks ``window_title``.

The judgement call under test: the guard BINDS when the staged window WAS a
browser (any domain drift aborts, whether or not a field declares one) OR
when a filled vault entry DECLARES a required domain (which fails CLOSED if
no origin can be read at all, browser or not). An undeclared entry in a
native (non-browser) window is untouched by either rule.

``origin_domain``/``is_browser`` are passed to ``stage_form`` as LITERALS in
most tests below (mirroring how the existing window-guard tests hardcode
``window_title`` rather than calling ``foreground_window_title()``) --
staging-time capture correctness is already covered by
test_grounding_origin.py's pure tests and by the one end-to-end sanity check
in ``test_matching_browser_origin_fills`` below, which DOES call the real
``foreground_origin()``. What matters for the tests in this file is what
``verify_staged_origin``/``verify_declared_domain`` see when EXECUTION
re-reads the live tree, which is what the ``grounding._default_provider``
swaps below exercise.

Following this project's own rule (see test_form_submit_gate.py's module
docstring): fakes stay strictly BELOW the tool-level gate -- the
accessibility-tree provider, the pyautogui actuator, and the foreground-window
reader. Every test drives the REAL ``ToolRegistry().run`` and the REAL
confirmation round-trip.
"""

from __future__ import annotations

import pytest

from eva.agent.action_model import AgentObservation
from eva.permissions.ledger import confirm_pending_action
from eva.screen import form_filler, grounding, screen_controller
from eva.screen.form_filler import FormField, SubmitSpec, foreground_origin, stage_form
from eva.tools.registry import ToolRegistry
from eva.vault import Vault


def _el(name: str, *, left: int, top: int, width: int = 80, height: int = 20, role: str = "Edit", value: str = "") -> grounding.RawElement:
    return grounding.RawElement(name=name, role=role, left=left, top=top, width=width, height=height, value=value)


def _address_bar(url: str) -> grounding.RawElement:
    return _el("Address and search bar", left=0, top=0, width=800, height=30, value=url)


# Email -> (90, 110), Password -> (90, 210), Submit -> (90, 310) -- same
# convention as test_form_submit_window_guard.py.
def _form_fields():
    return [
        _el("Email", left=50, top=100),
        _el("Password", left=50, top=200),
        _el("Submit", left=50, top=300, role="Button"),
    ]


class _InputRecorder:
    def __init__(self) -> None:
        self.clicks: list[tuple[int, int]] = []
        self.typed: list[str] = []

    def click(self, x, y, reason, action_id: str = "screen.click") -> AgentObservation:
        self.clicks.append((int(x), int(y)))
        return AgentObservation(action_id=action_id, success=True, raw_observation={"x": int(x), "y": int(y)}, summary="fake click")

    def type_text(self, text, reason, action_id: str = "screen.type_text") -> AgentObservation:
        self.typed.append(str(text))
        return AgentObservation(action_id=action_id, success=True, raw_observation={"chars": len(str(text))}, summary="fake type")

    def press(self, key, reason, action_id: str = "screen.press") -> AgentObservation:
        self.typed.append(f"KEY:{key}")
        return AgentObservation(action_id=action_id, success=True, raw_observation={"key": key}, summary="fake press")


@pytest.fixture
def gated_screen(monkeypatch, tmp_path):
    monkeypatch.setenv("EVA_GUI_GROUNDING_ENABLED", "1")
    monkeypatch.setenv("EVA_VAULT_ENABLED", "1")
    monkeypatch.setenv("EVA_VAULT_PATH", str(tmp_path / "vault.json"))
    monkeypatch.setattr(form_filler, "foreground_window_title", lambda: "Test App")
    monkeypatch.setattr(form_filler, "restore_window_focus", lambda window_title: None)

    recorder = _InputRecorder()
    monkeypatch.setattr(screen_controller, "click", recorder.click)
    monkeypatch.setattr(screen_controller, "type_text", recorder.type_text)
    monkeypatch.setattr(screen_controller, "press", recorder.press)
    yield recorder


def _confirm(spec_id: str, reason: str) -> dict:
    registry = ToolRegistry()
    gate_result = registry.run("screen.submit_form", spec_id=spec_id, reason=reason)
    assert gate_result.get("requires_confirmation") is True
    pending_id = gate_result["pending_id"]
    confirmed = confirm_pending_action(pending_id, override=bool(gate_result.get("risk_class") == "override"))
    assert confirmed.success is True
    executed = registry.run_approved(pending_id)
    assert isinstance(executed, dict)
    return executed


# -- 1. Matching domain fills -------------------------------------------------


def test_matching_browser_origin_fills(gated_screen, monkeypatch):
    elements = [_address_bar("https://mybank.com/login"), *_form_fields()]
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(elements))

    # The one place in this file that exercises the REAL staging-time capture
    # (foreground_origin()), not a literal -- everything else hardcodes
    # origin_domain/is_browser like the window-guard tests hardcode
    # window_title, since what those tests exercise is re-verification, not
    # capture.
    is_browser, origin_domain = foreground_origin()
    assert is_browser is True and origin_domain == "mybank.com"

    staged = stage_form(
        [FormField("Email", "me@example.com"), FormField("Password", "hunter2xyz")],
        reason="matching origin test",
        submit=SubmitSpec("click", label="Submit"),
        window_title="Test App",
        origin_domain=origin_domain,
        is_browser=is_browser,
    )
    outcome = _confirm(staged.spec_id, staged.reason)

    assert outcome["ok"] is True, outcome
    assert [s["status"] for s in outcome["steps"]] == ["filled", "filled"]
    assert gated_screen.clicks == [(90, 110), (90, 210), (90, 310)]
    assert gated_screen.typed == ["me@example.com", "hunter2xyz"]


# -- 2. Mismatched domain aborts, nothing typed ------------------------------


def test_mismatched_browser_origin_aborts_before_first_field(gated_screen, monkeypatch):
    staged = stage_form(
        [FormField("Email", "me@example.com")],
        reason="mismatched origin test",
        submit=SubmitSpec("none"),
        window_title="Test App",
        origin_domain="mybank.com",
        is_browser=True,
    )

    # Between staging and approval, the page (or the whole tab) changed to a
    # DIFFERENT site. Deliberately crafted to contain "mybank.com" as a
    # SUBSTRING ("mybank.com.evil.example") -- the guard must compare exact
    # domains, never containment, or this exact attack would sail through.
    phishing_elements = [_address_bar("https://mybank.com.evil.example/login"), *_form_fields()]
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(phishing_elements))

    outcome = _confirm(staged.spec_id, staged.reason)

    assert outcome["ok"] is False
    assert outcome["steps"][-1]["status"] == "origin_changed", outcome
    assert outcome["filled"] == 0
    assert gated_screen.clicks == [] and gated_screen.typed == [], "a domain mismatch must abort before the first click"
    assert "me@example.com" not in str(outcome)


def test_mismatched_origin_mid_form_stops_after_field_one(gated_screen, monkeypatch):
    staged_elements = [_address_bar("https://mybank.com/login"), *_form_fields()]
    evil_elements = [_address_bar("https://evil.example/login"), *_form_fields()]
    state = {"elements": staged_elements}
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(state["elements"]))

    staged = stage_form(
        [FormField("Email", "me@example.com"), FormField("Password", "hunter2xyz")],
        reason="mid form origin drift",
        submit=SubmitSpec("none"),
        window_title="Test App",
        origin_domain="mybank.com",
        is_browser=True,
    )

    # Field 1 (Email) sees the real site; the site changes before field 2's
    # pre-type check.
    real_click = screen_controller.click

    def click_then_drift(*args, **kwargs):
        result = real_click(*args, **kwargs)
        state["elements"] = evil_elements
        return result

    monkeypatch.setattr(screen_controller, "click", click_then_drift)

    outcome = _confirm(staged.spec_id, staged.reason)

    assert outcome["ok"] is False
    assert outcome["filled"] == 1
    assert [s["status"] for s in outcome["steps"]] == ["filled", "origin_changed"], outcome
    assert gated_screen.clicks == [(90, 110)]
    assert gated_screen.typed == ["me@example.com"]
    assert "hunter2xyz" not in str(outcome)


# -- 3. Declared-domain vault entry fails CLOSED when no origin is readable --


def test_declared_domain_entry_fails_closed_with_no_readable_origin(gated_screen, monkeypatch, tmp_path):
    # A NATIVE window: no address bar control at all in the tree.
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(_form_fields()))

    vault = Vault(tmp_path / "vault.json")
    assert vault.put("bank_pw", "hunter2xyz") is True
    assert vault.set_domain("bank_pw", "mybank.com") is True

    staged = stage_form(
        [FormField("Password", "@vault:bank_pw")],
        reason="declared domain, unreadable origin",
        submit=SubmitSpec("none"),
        window_title="Test App",
        origin_domain="",
        is_browser=False,
    )
    outcome = _confirm(staged.spec_id, staged.reason)

    assert outcome["ok"] is False
    assert outcome["steps"][-1]["status"] == "origin_mismatch", outcome
    # The click to focus the field may have happened, but the value must
    # never have been resolved or typed -- fail CLOSED means it never even
    # decrypts, let alone types.
    assert gated_screen.typed == [], "a declared-domain entry must never type when its origin cannot be verified"
    assert "hunter2xyz" not in str(outcome)


def test_declared_domain_entry_fills_when_origin_matches(gated_screen, monkeypatch, tmp_path):
    elements = [_address_bar("https://mybank.com/login"), *_form_fields()]
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(elements))

    vault = Vault(tmp_path / "vault.json")
    assert vault.put("bank_pw", "hunter2xyz") is True
    assert vault.set_domain("bank_pw", "mybank.com") is True

    staged = stage_form(
        [FormField("Password", "@vault:bank_pw")],
        reason="declared domain, matching origin",
        submit=SubmitSpec("none"),
        window_title="Test App",
        origin_domain="mybank.com",
        is_browser=True,
    )
    outcome = _confirm(staged.spec_id, staged.reason)

    assert outcome["ok"] is True, outcome
    assert gated_screen.typed == ["hunter2xyz"]


def test_declared_domain_entry_aborts_on_wrong_domain_even_in_a_browser(gated_screen, monkeypatch, tmp_path):
    # The window IS a browser, and its own general origin check would pass
    # (it stays on the same site throughout) -- but the vault entry is bound
    # to a DIFFERENT domain than the one currently showing, which must still
    # fail closed for that field specifically.
    elements = [_address_bar("https://not-my-bank.example/login"), *_form_fields()]
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(elements))

    vault = Vault(tmp_path / "vault.json")
    assert vault.put("bank_pw", "hunter2xyz") is True
    assert vault.set_domain("bank_pw", "mybank.com") is True

    staged = stage_form(
        [FormField("Password", "@vault:bank_pw")],
        reason="declared domain, wrong site",
        submit=SubmitSpec("none"),
        window_title="Test App",
        origin_domain="not-my-bank.example",
        is_browser=True,
    )
    outcome = _confirm(staged.spec_id, staged.reason)

    assert outcome["ok"] is False
    assert outcome["steps"][-1]["status"] == "origin_mismatch", outcome
    assert gated_screen.typed == []


# -- 4. Undeclared entry in a native window: unchanged behaviour ------------


def test_undeclared_entry_in_native_window_fills_unchanged(gated_screen, monkeypatch, tmp_path):
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(_form_fields()))

    vault = Vault(tmp_path / "vault.json")
    assert vault.put("note_pw", "plainvalue") is True
    # No set_domain call -- this entry is undeclared, exactly like every
    # entry that existed before Phase 67.

    staged = stage_form(
        [FormField("Password", "@vault:note_pw")],
        reason="undeclared entry native window",
        submit=SubmitSpec("none"),
        window_title="Test App",
        origin_domain="",
        is_browser=False,
    )
    outcome = _confirm(staged.spec_id, staged.reason)

    assert outcome["ok"] is True, outcome
    assert gated_screen.typed == ["plainvalue"]


def test_pre_phase67_staged_form_defaults_are_inert(gated_screen, monkeypatch):
    """A StagedForm built without ever mentioning origin_domain/is_browser
    (as every pre-Phase-67 caller does) must behave exactly as it always did
    -- the guard must never activate on defaulted fields."""
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(_form_fields()))
    staged = stage_form(
        [FormField("Email", "me@example.com")],
        reason="no origin info at all",
        submit=SubmitSpec("none"),
        window_title="Test App",
    )
    assert staged.origin_domain == "" and staged.is_browser is False
    outcome = _confirm(staged.spec_id, staged.reason)
    assert outcome["ok"] is True, outcome


# -- 5. The final submit action is re-checked too, not just the fields ------


def test_origin_drift_before_submit_click_aborts(gated_screen, monkeypatch):
    staged_elements = [_address_bar("https://mybank.com/login"), *_form_fields()]
    evil_elements = [_address_bar("https://evil.example/login"), *_form_fields()]
    state = {"elements": staged_elements}
    monkeypatch.setattr(grounding, "_default_provider", lambda: list(state["elements"]))

    # The site changes only once the Email field has actually been typed into
    # -- i.e. the field itself filled correctly, and only the submit click is
    # what must be refused.
    real_type_text = screen_controller.type_text

    def type_then_drift(*args, **kwargs):
        result = real_type_text(*args, **kwargs)
        state["elements"] = evil_elements
        return result

    monkeypatch.setattr(screen_controller, "type_text", type_then_drift)

    staged = stage_form(
        [FormField("Email", "me@example.com")],
        reason="origin drift before submit",
        submit=SubmitSpec("click", label="Submit"),
        window_title="Test App",
        origin_domain="mybank.com",
        is_browser=True,
    )
    outcome = _confirm(staged.spec_id, staged.reason)

    assert outcome["ok"] is False
    assert outcome["filled"] == 1
    assert outcome["steps"][-1]["status"] == "origin_changed", outcome
    assert gated_screen.clicks == [(90, 110)], "the submit click must never have happened"
    assert gated_screen.typed == ["me@example.com"]
