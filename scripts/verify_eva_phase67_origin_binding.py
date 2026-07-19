"""Standalone verifier for Phase 67: origin binding, the identity half of the
phishing gap left open by Phase 62-64's staged form submission.

GUI grounding (Phase 56) matches LABELS, not origin: a hostile page with a
field literally named "Email" gets ``@vault:email`` filled into it regardless
of which site it is actually on. Phase 63 re-verifies the foreground WINDOW
before every field and before the final submit -- but that guard cannot see
this class of attack, because a phishing page can simply be titled and styled
to look exactly like the real thing while living at a different domain.

The fix reads the domain from the browser's own address bar. Chrome/Edge
expose it as an Edit control in the SAME accessibility tree grounding already
walks (``apps/playbooks.py`` already knew its label, "Address and search
bar"), and its UIA ValuePattern holds the current page's URL -- so the one
real gap was that ``grounding.RawElement`` had no field to carry a value at
all. ``RawElement.value`` is defaulted to ``""`` specifically so every
existing fabricated-tree test across this project (there are many) keeps
constructing it, positionally or by keyword, unchanged.

The judgement call this phase turns on, and the one this file spends the most
effort proving: a native app form (Notepad, an installer, a desktop login)
has NO origin at all, so "no origin readable" must neither silently pass NOR
blanket-fail. The rule implemented in ``eva.screen.form_filler``:

  (a) The guard BINDS whenever the staged window WAS a browser (detected by
      the address-bar control's presence in the tree, not a process-name
      guess). Any domain drift for a browser-staged form aborts -- the
      general phishing defense, independent of any vault declaration.
  (b) Independently, a vault entry that DECLARES a required domain
      (``eva.vault.store.Vault.set_domain``) binds too, even in a window that
      does not look like a browser, and FAILS CLOSED if no origin can be read
      at all -- that is the entire point of declaring one.
  (c) An undeclared field in a native (non-browser) window is untouched by
      either rule: unchanged from every phase before this one.

Honesty notes, load-bearing for what this phase does and does not claim:
  * The comparison is DOMAIN, never the full URL string -- the omnibox
    display text is routinely shortened (scheme hidden, path trimmed).
  * This binds to what the BROWSER CHROME reports, which is the right trust
    anchor (page content cannot rewrite it) -- but it is a proxy for the
    DOM's true origin, not the real thing, and is never claimed to be.
  * Only Chrome/Edge are known to expose this control under this name; other
    browsers and kiosk/fullscreen modes have no readable origin.
  * The desktop this was authored on is locked/disconnected
    (GetForegroundWindow() returns 0), so live-driving a real Chrome window
    is NOT possible right now -- this is built injectable, exactly like every
    other grounding property in this project, and real-browser validation is
    still outstanding (see the README).

Following this project's rule for this test surface (see
test_form_submit_gate.py's module docstring): injection is allowed BELOW the
tool-level gate (which controls exist on screen, the pyautogui actuator, the
foreground-window/origin readers) but never ACROSS it. Every gate-crossing
check below drives the REAL ``ToolRegistry().run``, the REAL confirmation
round-trip, and the REAL ``Vault``.

Fully offline: no network, no LLM, no real mouse/keyboard movement, and the
vault + pending-action ledger are redirected to a throwaway temp directory
before anything that reads those env vars is imported.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    tmpdir = tempfile.TemporaryDirectory(prefix="eva-phase67-verify-")
    tmp_path = Path(tmpdir.name)
    os.environ["EVA_VAULT_PATH"] = str(tmp_path / "vault.json")
    os.environ["EVA_VAULT_ENABLED"] = "1"
    os.environ["EVA_PENDING_ACTION_LEDGER_PATH"] = str(tmp_path / "pending_actions.jsonl")
    os.environ["EVA_GUI_GROUNDING_ENABLED"] = "1"
    try:
        return _run(tmp_path)
    finally:
        tmpdir.cleanup()


def _el(grounding, name, *, left, top, width=80, height=20, role="Edit", value=""):
    return grounding.RawElement(name=name, role=role, left=left, top=top, width=width, height=height, value=value)


def _address_bar(grounding, url: str):
    return _el(grounding, "Address and search bar", left=0, top=0, width=800, height=30, value=url)


# Email -> (90, 110), Password -> (90, 210), Submit -> (90, 310).
def _form_fields(grounding):
    return [
        _el(grounding, "Email", left=50, top=100),
        _el(grounding, "Password", left=50, top=200),
        _el(grounding, "Submit", left=50, top=300, role="Button"),
    ]


class _InputRecorder:
    def __init__(self, AgentObservation) -> None:
        self._obs = AgentObservation
        self.clicks: list[tuple[int, int]] = []
        self.typed: list[str] = []

    def click(self, x, y, reason, action_id: str = "screen.click"):
        self.clicks.append((int(x), int(y)))
        return self._obs(action_id=action_id, success=True, raw_observation={"x": int(x), "y": int(y)}, summary="fake click")

    def type_text(self, text, reason, action_id: str = "screen.type_text"):
        self.typed.append(str(text))
        return self._obs(action_id=action_id, success=True, raw_observation={"chars": len(str(text))}, summary="fake type")

    def press(self, key, reason, action_id: str = "screen.press"):
        self.typed.append(f"KEY:{key}")
        return self._obs(action_id=action_id, success=True, raw_observation={"key": key}, summary="fake press")


def _verify_raw_element_backward_compat(grounding) -> None:
    # Positional construction exactly as it existed before Phase 67 (8
    # positional/keyword args, no `value`) must keep working unchanged --
    # this is what every fabricated-tree test across the project relies on.
    el = grounding.RawElement("Submit", "button", 100, 200, 80, 30)
    check(el.value == "", f"RawElement.value must default to '', got {el.value!r}")
    el2 = grounding.RawElement(name="X", role="edit", left=0, top=0, width=10, height=10)
    check(el2.value == "", "keyword construction without value must also default to ''")


def _verify_pure_origin_functions(grounding) -> None:
    bar = _address_bar(grounding, "https://mybank.com:8443/login?x=1")
    check(grounding.is_browser_window([bar]) is True, "an address bar control must be detected as a browser")
    origin = grounding.read_origin([bar])
    check(origin is not None and origin.domain == "mybank.com", f"expected domain mybank.com, got {origin}")

    scheme_less = _address_bar(grounding, "mybank.com/accounts")
    origin2 = grounding.read_origin([scheme_less])
    check(origin2 is not None and origin2.domain == "mybank.com", f"scheme-less omnibox text must still parse: {origin2}")

    empty_bar = _address_bar(grounding, "")
    check(grounding.is_browser_window([empty_bar]) is True, "an address bar with no value is still a browser")
    check(grounding.read_origin([empty_bar]) is None, "an unreadable omnibox value must yield no origin, not a guess")

    native = _form_fields(grounding)
    check(grounding.is_browser_window(native) is False, "a tree with no address bar control must not look like a browser")
    check(grounding.read_origin(native) is None, "a native window must have no readable origin")


def _verify_describe_staged_form_shows_domain(form_filler) -> None:
    from datetime import datetime, timezone

    browser_spec = form_filler.StagedForm(
        spec_id="preview",
        reason="preview",
        fields=(form_filler.FormField("Email", "me@example.com"),),
        submit=form_filler.SubmitSpec("none"),
        window_title="Sign in - Google Chrome",
        created_at=datetime.now(timezone.utc),
        origin_domain="mybank.com",
        is_browser=True,
    )
    manifest = form_filler.describe_staged_form(browser_spec)
    check("mybank.com" in manifest, f"the manifest must surface the page domain for a browser-staged form: {manifest!r}")
    check("address bar" in manifest.lower(), "the manifest must be honest about WHERE the domain came from")

    native_spec = form_filler.StagedForm(
        spec_id="preview2",
        reason="preview",
        fields=(form_filler.FormField("Email", "me@example.com"),),
        submit=form_filler.SubmitSpec("none"),
        window_title="Untitled - Notepad",
        created_at=datetime.now(timezone.utc),
    )
    manifest2 = form_filler.describe_staged_form(native_spec)
    check("Page domain" not in manifest2, f"a native (non-browser) staged form must not claim a page domain: {manifest2!r}")


def _run(tmp_path: Path) -> int:
    from backend.eva.agent.action_model import AgentObservation
    from backend.eva.permissions.ledger import confirm_pending_action
    from backend.eva.screen import form_filler, grounding, screen_controller
    from backend.eva.screen.form_filler import FormField, SubmitSpec, stage_form
    from backend.eva.tools.registry import ToolRegistry
    from backend.eva.vault import Vault
    from scripts import verify_eva_all

    _verify_raw_element_backward_compat(grounding)
    _verify_pure_origin_functions(grounding)
    _verify_describe_staged_form_shows_domain(form_filler)

    registry = ToolRegistry()

    def confirm(spec_id: str, reason: str) -> dict:
        gate_result = registry.run("screen.submit_form", spec_id=spec_id, reason=reason)
        check(gate_result.get("requires_confirmation") is True, f"submission must stay confirm-gated: {gate_result}")
        pending_id = gate_result["pending_id"]
        confirmed = confirm_pending_action(pending_id, override=bool(gate_result.get("risk_class") == "override"))
        check(confirmed.success is True, f"ledger confirmation must succeed: {confirmed}")
        executed = registry.run_approved(pending_id)
        check(isinstance(executed, dict), f"run_approved must return the outcome dict, got {executed!r}")
        return executed

    recorder = _InputRecorder(AgentObservation)
    saved_provider = grounding._default_provider
    saved_click = screen_controller.click
    saved_type_text = screen_controller.type_text
    saved_press = screen_controller.press
    saved_window_title_fn = form_filler.foreground_window_title
    saved_restore_fn = form_filler.restore_window_focus

    grounding._default_provider = lambda: _form_fields(grounding)
    screen_controller.click = recorder.click
    screen_controller.type_text = recorder.type_text
    screen_controller.press = recorder.press
    form_filler.foreground_window_title = lambda: "Test App"
    form_filler.restore_window_focus = lambda window_title: None

    try:
        # 1. Matching domain -> fills, through the REAL gate.
        grounding._default_provider = lambda: [_address_bar(grounding, "https://mybank.com/login"), *_form_fields(grounding)]
        is_browser, origin_domain = form_filler.foreground_origin()
        check(is_browser is True and origin_domain == "mybank.com", f"foreground_origin() plumbing broken: {(is_browser, origin_domain)}")

        staged = stage_form(
            [FormField("Email", "me@example.com"), FormField("Password", "hunter2xyz")],
            reason="phase67 matching origin",
            submit=SubmitSpec("click", label="Submit"),
            window_title="Test App",
            origin_domain=origin_domain,
            is_browser=is_browser,
        )
        outcome = confirm(staged.spec_id, staged.reason)
        check(outcome["ok"] is True, f"a matching origin must fill normally: {outcome}")
        check(recorder.clicks == [(90, 110), (90, 210), (90, 310)], recorder.clicks)
        check(recorder.typed == ["me@example.com", "hunter2xyz"], recorder.typed)

        # 2. Mismatched domain -> aborts, NOTHING typed. The mismatch is
        # deliberately crafted as a domain containing the expected one as a
        # SUBSTRING ("mybank.com.evil.example" contains "mybank.com") -- a
        # containment-based comparison would let exactly this attack through.
        recorder.clicks.clear()
        recorder.typed.clear()
        staged2 = stage_form(
            [FormField("Email", "me@example.com")],
            reason="phase67 mismatched origin",
            submit=SubmitSpec("none"),
            window_title="Test App",
            origin_domain="mybank.com",
            is_browser=True,
        )
        grounding._default_provider = lambda: [_address_bar(grounding, "https://mybank.com.evil.example/login"), *_form_fields(grounding)]
        outcome2 = confirm(staged2.spec_id, staged2.reason)
        check(outcome2["ok"] is False, f"a domain mismatch must abort: {outcome2}")
        check(outcome2["steps"][-1]["status"] == "origin_changed", outcome2)
        check(outcome2["filled"] == 0, outcome2)
        check(recorder.clicks == [] and recorder.typed == [], "a domain mismatch must abort BEFORE the first click")
        check("me@example.com" not in str(outcome2), "the outcome must stay value-free on this abort path")

        # 3. Declared-domain vault entry + unreadable origin (native window)
        # -> FAILS CLOSED. This is the phase's core judgement call.
        recorder.clicks.clear()
        recorder.typed.clear()
        grounding._default_provider = lambda: _form_fields(grounding)  # native: no address bar at all
        vault = Vault(Path(os.environ["EVA_VAULT_PATH"]))
        check(vault.put("bank_pw", "hunter2xyz") is True, "seeding the vault must succeed (DPAPI on this account)")
        check(vault.set_domain("bank_pw", "mybank.com") is True, "declaring a domain on an existing entry must succeed")
        check(vault.entry_domain("bank_pw") == "mybank.com", "entry_domain must report the declared binding")

        staged3 = stage_form(
            [FormField("Password", "@vault:bank_pw")],
            reason="phase67 declared domain unreadable origin",
            submit=SubmitSpec("none"),
            window_title="Test App",
            origin_domain="",
            is_browser=False,
        )
        outcome3 = confirm(staged3.spec_id, staged3.reason)
        check(outcome3["ok"] is False, f"a declared-domain entry with no readable origin must fail closed: {outcome3}")
        check(outcome3["steps"][-1]["status"] == "origin_mismatch", outcome3)
        check(recorder.typed == [], "the value must never be typed -- fail closed means it never even decrypts")
        check("hunter2xyz" not in str(outcome3), "the outcome must stay value-free")

        # 3b. The SAME declared-domain entry fills normally once a matching
        # origin IS readable -- proving (3) is a real check, not dead code
        # that fails unconditionally.
        recorder.clicks.clear()
        recorder.typed.clear()
        grounding._default_provider = lambda: [_address_bar(grounding, "https://mybank.com/login"), *_form_fields(grounding)]
        staged3b = stage_form(
            [FormField("Password", "@vault:bank_pw")],
            reason="phase67 declared domain matching origin",
            submit=SubmitSpec("none"),
            window_title="Test App",
            origin_domain="mybank.com",
            is_browser=True,
        )
        outcome3b = confirm(staged3b.spec_id, staged3b.reason)
        check(outcome3b["ok"] is True, f"a declared-domain entry must fill when the origin genuinely matches: {outcome3b}")
        check(recorder.typed == ["hunter2xyz"], recorder.typed)

        # 4. Undeclared entry in a native (originless) window -> UNCHANGED
        # behaviour: still fills, exactly as every phase before this one.
        recorder.clicks.clear()
        recorder.typed.clear()
        grounding._default_provider = lambda: _form_fields(grounding)
        check(vault.put("note_pw", "plainvalue") is True, "seeding an undeclared entry must succeed")
        check(vault.entry_domain("note_pw") == "", "sanity: this entry declares no domain")
        staged4 = stage_form(
            [FormField("Password", "@vault:note_pw")],
            reason="phase67 undeclared entry native window",
            submit=SubmitSpec("none"),
            window_title="Test App",
            origin_domain="",
            is_browser=False,
        )
        outcome4 = confirm(staged4.spec_id, staged4.reason)
        check(outcome4["ok"] is True, f"an undeclared entry in a native window must fill unchanged: {outcome4}")
        check(recorder.typed == ["plainvalue"], recorder.typed)

        # 5. A StagedForm built with NO origin info at all (every pre-Phase-67
        # caller) must be completely inert to this guard.
        recorder.clicks.clear()
        recorder.typed.clear()
        grounding._default_provider = lambda: _form_fields(grounding)
        staged5 = stage_form(
            [FormField("Email", "me@example.com")],
            reason="phase67 backward compat, no origin info",
            submit=SubmitSpec("none"),
            window_title="Test App",
        )
        check(staged5.origin_domain == "" and staged5.is_browser is False, "StagedForm defaults must be the inert values")
        outcome5 = confirm(staged5.spec_id, staged5.reason)
        check(outcome5["ok"] is True, f"a pre-Phase-67-shaped staged form must behave exactly as before: {outcome5}")

        # 6. The final SUBMIT action is re-checked too, not just the fields:
        # the site changes only after the one field has already been typed.
        recorder.clicks.clear()
        recorder.typed.clear()
        state = {"elements": [_address_bar(grounding, "https://mybank.com/login"), *_form_fields(grounding)]}
        grounding._default_provider = lambda: list(state["elements"])
        real_type_text = recorder.type_text

        def type_then_drift(text, reason, action_id: str = "screen.type_text"):
            result = real_type_text(text, reason, action_id=action_id)
            state["elements"] = [_address_bar(grounding, "https://evil.example/login"), *_form_fields(grounding)]
            return result

        screen_controller.type_text = type_then_drift
        staged6 = stage_form(
            [FormField("Email", "me@example.com")],
            reason="phase67 drift before submit",
            submit=SubmitSpec("click", label="Submit"),
            window_title="Test App",
            origin_domain="mybank.com",
            is_browser=True,
        )
        outcome6 = confirm(staged6.spec_id, staged6.reason)
        check(outcome6["ok"] is False, f"origin drift before the submit click must abort: {outcome6}")
        check(outcome6["filled"] == 1, outcome6)
        check(outcome6["steps"][-1]["status"] == "origin_changed", outcome6)
        check(recorder.clicks == [(90, 110)], "the submit click must never have happened")
        screen_controller.type_text = recorder.type_text
    finally:
        grounding._default_provider = saved_provider
        screen_controller.click = saved_click
        screen_controller.type_text = saved_type_text
        screen_controller.press = saved_press
        form_filler.foreground_window_title = saved_window_title_fn
        form_filler.restore_window_focus = saved_restore_fn

    # 7. Console wiring: `bind vault`/`unbind vault` (never a planner/registry
    # tool -- like every other vault command, the model must never reach it).
    from backend.eva.core.fast_commands import maybe_handle_fast_command

    vault_path = Path(os.environ["EVA_VAULT_PATH"])
    vault2 = Vault(vault_path)
    check(vault2.put("work_login", "s3cr3t") is True, "seeding a fresh entry for the console-command test must succeed")

    console_registry = ToolRegistry()

    reply, kind = maybe_handle_fast_command("bind vault work_login to domain example.com", console_registry, {})
    check(kind == "fast-command", f"'bind vault' must be handled as a fast command, got {kind!r}")
    check("example.com" in str(reply), f"the bind confirmation must name the domain: {reply!r}")
    check(vault2.entry_domain("work_login") == "example.com", "the console command must actually bind the domain")
    check("s3cr3t" not in str(reply), "the bind confirmation must never echo the saved value")

    reply2, kind2 = maybe_handle_fast_command("unbind vault work_login", console_registry, {})
    check(kind2 == "fast-command", f"'unbind vault' must be handled as a fast command, got {kind2!r}")
    check(vault2.entry_domain("work_login") == "", "the console command must actually clear the domain")

    check(vault2.put("bank_pw2", "hunter2", domain="mybank.com") is True, "seeding a bound entry for the list-command test must succeed")
    list_reply2, _ = maybe_handle_fast_command("vault list", console_registry, {})
    check("mybank.com" in str(list_reply2), f"'vault list' must surface a declared domain binding: {list_reply2!r}")
    check("hunter2" not in str(list_reply2), "'vault list' must never show a value")

    # `bind vault`/`unbind vault` must never become registry/planner tools --
    # the vault must stay unreachable from the model, same invariant Phase 62
    # already established for save/forget.
    planner_names = {str(spec.get("name", "")) for spec in ToolRegistry().planner_specs()}
    for forbidden in ("vault.bind", "vault.unbind", "vault.set_domain"):
        check(forbidden not in planner_names, f"{forbidden} must not be planner-reachable")

    # Registration.
    name = "verify_eva_phase67_origin_binding.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 67 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 67 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 67 verifier")

    print(
        "PASS: Phase 67 origin binding -- the identity half of the phishing gap left open since Phase 62. "
        "GUI grounding matches labels, not sites, so a hostile page with a field literally named 'Email' would "
        "get a saved credential filled into it regardless of which domain it actually lives on; Phase 63's window "
        "guard cannot see this because a phishing page can be titled and styled to look exactly like the real "
        "thing. Chrome/Edge already expose their address bar in the same accessibility tree grounding walks -- the "
        "one real gap was that RawElement had nowhere to carry a control's value, closed with a DEFAULTED field so "
        "every existing fabricated-tree test keeps constructing it unchanged (pinned directly above). "
        "screen_submit_form now re-verifies the browser origin (domain only, never the full URL, since the omnibox "
        "display text is routinely shortened) before every field and before the final submit, exactly mirroring "
        "how it already re-verifies the window. The core judgement call: the guard binds when the staged window "
        "WAS a browser (any domain drift aborts, whether or not a field declares one, proven here including a "
        "domain crafted to contain the real one as a SUBSTRING -- a containment check would have let it through) "
        "OR when a vault entry DECLARES a required domain, which FAILS CLOSED if no origin can be read at all -- "
        "proven never resolving or typing the value in that case, then proven NOT dead code by filling normally "
        "once a matching origin is readable. An undeclared entry in a native, originless window (Notepad, an "
        "installer) is untouched by either rule and fills exactly as it did before this phase existed, and a "
        "StagedForm built with no origin info at all (every pre-Phase-67 caller) is completely inert to the new "
        "guard. New console commands `bind vault <name> to domain <domain>` / `unbind vault <name>` stay off the "
        "planner surface like every other vault command. NOT covered: a real Chrome window -- the desktop this was "
        "authored on is locked/disconnected, so this is built injectable and live-validated by design; that "
        "validation is still outstanding."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
