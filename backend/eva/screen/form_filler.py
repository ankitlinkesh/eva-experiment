"""Filling a form — chaining locate -> click -> type, safely (Phase 58).

Phase 56 made a single field clickable by label and Phase 57 made the screen
observable. This composes them into the thing people actually ask for: "fill in
this form." For each (label, value) it clicks the field to focus it and types the
value — going through the ordinary gated tools every step, so it inherits the
confidence gate, the real-input gate, and the Phase 55 risk escalation. It adds
no new authority; it is pure orchestration over tools NOVA already has.

Three safety commitments:

  * **It never records the values.** A form value is often a password or a
    payment detail. A :class:`FillStep` carries only the field label, whether the
    value looked like a live secret, and the outcome — never the value itself.
    Nothing here logs, traces, or returns the typed text.
  * **It stops rather than blunders.** The moment a field cannot be found (or a
    click/type is refused, e.g. real input is off), it stops and reports where —
    it does not keep typing values into the wrong places on a half-understood
    form.
  * **It is driven only from the trusted console.** Like NL rule creation, this
    is reached from a typed fast-command, never wired as a planner tool — so
    untrusted content (Phase 40) cannot make NOVA type attacker-chosen values
    into a form.

The executor is injectable, so the orchestration is tested without a real
desktop; the default routes every step through the real ToolRegistry gate.

Phase 62 adds a second path alongside ``fill_form``: staging. ``screen.type_text``
is confirm-class, so gating each field individually (as ``fill_form`` does) stalls
a real submission at field 1 asking to confirm typing. ``stage_form`` lets the
trusted console record a whole form (fields -- literal or ``@vault:name``
references -- plus what to do when done) as one ``StagedForm`` behind an opaque
``spec_id``; the gated tool ``screen.submit_form`` (see ``screen_tools.py``) takes
only that id and, after a single approval, performs the whole form. See
``describe_staged_form`` for the value-free manifest the approval reads.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

Executor = Callable[..., dict]

# Phase 62: a field value of this form is a REFERENCE into the vault, not a
# literal. It is safe to carry through staging, the gate's pending-call args,
# and the ledger, because it resolves to plaintext only inside the approved
# submit handler (see screen_tools.screen_submit_form) -- never here.
VAULT_PREFIX = "@vault:"


def is_vault_ref(value: str) -> bool:
    return str(value or "").startswith(VAULT_PREFIX)


def vault_ref_name(value: str) -> str | None:
    """"@vault:email" -> "email". None if ``value`` is not a vault reference."""
    text = str(value or "")
    if not text.startswith(VAULT_PREFIX):
        return None
    name = text[len(VAULT_PREFIX) :].strip()
    return name or None


@dataclass(frozen=True)
class FormField:
    """One field to fill. ``value`` is sensitive and never leaves this object."""

    label: str
    value: str


@dataclass(frozen=True)
class FillStep:
    """The outcome of one field — deliberately value-free."""

    label: str
    status: str          # filled | not_found | click_refused | type_refused
    secret: bool = False  # did the value look like a live secret?
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FillOutcome:
    steps: list[FillStep] = field(default_factory=list)
    filled: int = 0
    ok: bool = False
    stopped_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"steps": [s.as_dict() for s in self.steps], "filled": self.filled, "ok": self.ok, "stopped_reason": self.stopped_reason}


# -- staging a form for one-shot, gated submission (Phase 62) ---------------
#
# `fill_form` above gates every keystroke individually, and `screen.type_text`
# is confirm-class -- so a real call stalls at field 1 asking to confirm typing,
# forever, one field at a time. The fix is to gate the whole submission ONCE:
# the trusted console stages a form (fields, values or vault refs, and what to
# do when done) and gets back an opaque `spec_id`. The gated tool
# `screen.submit_form` takes ONLY that id; the gate gets to see the value-free
# manifest (`describe_staged_form`) and approves the id, never a value. After
# approval the handler pops the staged form (single-use) and does every
# click/type/submit itself, calling the screen_tools functions directly rather
# than re-entering the gate -- see the loud comment in screen_tools.py.
#
# This store mirrors `eva.security.tool_gate._PENDING_CALLS`: a module-level
# dict, single-use pop, and a TTL so a stale id cannot be replayed long after
# the console session that staged it is gone.


@dataclass(frozen=True)
class SubmitSpec:
    """What to do once every field is filled."""

    mode: str          # "click" | "press" | "none"
    label: str = ""    # for "click", e.g. "Submit"
    key: str = ""      # for "press", e.g. "enter"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StagedForm:
    """A form staged from the trusted console, waiting for gate approval.

    ``fields`` may hold literal values or ``@vault:name`` references -- either
    way this object never holds a decrypted secret; a vault ref only resolves
    to plaintext inside the post-approval submit handler.
    """

    spec_id: str
    reason: str
    fields: tuple[FormField, ...]
    submit: SubmitSpec
    window_title: str
    created_at: datetime
    # Phase 67: the browser origin (domain) at STAGING time, and whether the
    # staged window looked like a browser at all -- see verify_staged_origin
    # below for how these bind. "" / False are the safe defaults for every
    # existing caller (including every pre-Phase-67 test) that never learned
    # about origin binding: they mean "not a browser", which is exactly the
    # native-app case the guard must not touch.
    origin_domain: str = ""
    is_browser: bool = False


_STAGED_FORMS: dict[str, StagedForm] = {}
_STAGE_TTL_SECONDS = 300


def _staging_expired(staged: StagedForm) -> bool:
    age = (datetime.now(timezone.utc) - staged.created_at).total_seconds()
    return age > _STAGE_TTL_SECONDS


def stage_form(
    fields: Sequence[FormField | tuple[str, str]],
    *,
    reason: str,
    submit: SubmitSpec,
    window_title: str = "",
    origin_domain: str = "",
    is_browser: bool = False,
) -> StagedForm:
    """Stage a form for one-shot gated submission. Returns the staged record.

    Called only from the trusted console (mirrors ``fill_form``'s trust
    boundary): the caller decides the fields and the submit action, and gets
    back a ``spec_id`` opaque enough that nothing downstream needs to see a
    value again until an approved handler resolves it.

    ``origin_domain``/``is_browser`` (Phase 67) are captured the same way
    ``window_title`` already is -- the caller reads the CURRENT foreground
    surface (see :func:`foreground_origin`) and passes the result in, rather
    than this function reaching out on its own; that keeps staging a pure
    recording step and matches the existing ``window_title`` pattern exactly.
    """
    normalized = tuple(
        f if isinstance(f, FormField) else FormField(str(f[0]), str(f[1])) for f in fields
    )
    spec_id = "fs_" + uuid.uuid4().hex[:12]
    staged = StagedForm(
        spec_id=spec_id,
        reason=str(reason or ""),
        fields=normalized,
        submit=submit,
        window_title=str(window_title or ""),
        created_at=datetime.now(timezone.utc),
        origin_domain=str(origin_domain or ""),
        is_browser=bool(is_browser),
    )
    _STAGED_FORMS[spec_id] = staged
    return staged


def peek_staged_form(spec_id: str) -> StagedForm | None:
    """Look up a staged form WITHOUT consuming it. None if unknown or expired."""
    staged = _STAGED_FORMS.get(str(spec_id or ""))
    if staged is None:
        return None
    if _staging_expired(staged):
        # Expired: drop it here too, so a lookup after the TTL cannot linger.
        _STAGED_FORMS.pop(str(spec_id or ""), None)
        return None
    return staged


def pop_staged_form(spec_id: str) -> StagedForm | None:
    """Consume a staged form -- single use. None if unknown or expired.

    This is the injection defense for ``screen.submit_form``: the tool is
    inert without an id this store actually issued, and once popped the same
    id cannot be replayed.
    """
    staged = _STAGED_FORMS.pop(str(spec_id or ""), None)
    if staged is None:
        return None
    if _staging_expired(staged):
        return None
    return staged


def describe_staged_form(spec: StagedForm) -> str:
    """The value-free manifest a human reads before approving the submission.

    Shows vault NAMES (never vault values) and literal values IN FULL -- the
    user typed the literals seconds ago in the same console session, so they
    are not secret, and seeing them is what makes the approval informed.
    """
    header = (
        f'Fill and submit a form in "{spec.window_title}":'
        if spec.window_title
        else "Fill and submit a form:"
    )
    lines = [header]
    if spec.is_browser:
        # Read from the browser's own address bar, not the DOM's true origin
        # -- see grounding.py's Phase 67 section for why that distinction
        # matters and what it does and does not protect against.
        if spec.origin_domain:
            lines.append(f"  Page domain: {spec.origin_domain} (from the browser's address bar)")
        else:
            lines.append("  Page domain: unreadable (the address bar could not be read at staging time)")
    for index, item in enumerate(spec.fields, start=1):
        if is_vault_ref(item.value):
            name = vault_ref_name(item.value) or "?"
            lines.append(f"  {index}. {item.label}  <- saved: {name}  (value hidden)")
        else:
            lines.append(f'  {index}. {item.label}  <- "{item.value}"')
    if spec.submit.mode == "click" and spec.submit.label:
        lines.append(f'  Then: click "{spec.submit.label}"')
    elif spec.submit.mode == "press" and spec.submit.key:
        lines.append(f'  Then: press "{spec.submit.key}"')
    return "\n".join(lines)


def foreground_window_title() -> str:
    """Best-effort title of the current foreground window. Never raises.

    Reuses the same window lookup ``screen.observe`` already relies on (see
    ``screen_observer.get_active_window_title``); returns "" on any failure
    (unsupported platform, no foreground window, import error, ...) so a
    console staging a form never fails just because the title is unavailable.
    """
    try:
        from .screen_observer import get_active_window_title

        return str(get_active_window_title() or "")
    except Exception:
        return ""


# -- re-verifying the window before typing (Phase 63) ------------------------
#
# StagedForm captures window_title at STAGING time, and it is shown in the
# approval manifest -- but between staging, human approval, and execution the
# foreground window can change (a notification, an alt-tab, or -- as happened
# live-driving this against a real browser -- a terminal simply holding
# focus while the human approves in it). Without re-checking, screen_tools
# would type the user's decrypted vault value into whatever window happens to
# be in front. See screen_tools.screen_submit_form for where this is called,
# once before EVERY field (not just once at the start of the run).
#
# The matching rule is deliberately NOT exact string equality on the full
# title. A real web page can legitimately rewrite its own document.title
# while it is being filled in -- the page this defect was found on does
# exactly that -- so an exact-equality check would abort mid-fill on a page
# merely updating itself, which is not the harm this guard exists to catch.
# Browser chrome (and many native apps) appends a STABLE suffix to the page/
# document title -- "<page title> - Google Chrome" -- and a genuine window
# switch (Chrome -> a terminal) changes that suffix, not just the leading
# page-title text. So "same window" here means "same trailing '- App Name'
# segment", which tolerates a live page rewriting its own title while still
# catching a real foreground-window change.
#
# When a title has no " - " to split on, its identity IS the whole title --
# meaning ANY change of that title aborts. That is deliberately the safe
# direction: without a recognizable app suffix to key on, we cannot tell "the
# page renamed itself" from "the window changed", so we treat any drift as a
# potential window change rather than risk typing into the wrong place.
def _window_identity(title: str) -> str:
    text = str(title or "").strip()
    if not text:
        return ""
    if " - " in text:
        return text.rsplit(" - ", 1)[1].strip()
    return text


def verify_staged_window(staged: "StagedForm") -> str | None:
    """``None`` if the current foreground window still matches the one this
    form was staged against; otherwise a human-readable reason it does not.

    Fails SAFE in both directions: an empty staged title means "unknown at
    staging time, cannot verify" and is itself a reason to refuse (never
    silently proceed blind), and any identity mismatch (see
    ``_window_identity``) is reported as a window change. Callers should stop
    the whole run -- and type nothing -- on any non-``None`` return.
    """
    expected = str(staged.window_title or "").strip()
    if not expected:
        return "the target window was not recorded when this form was staged, so it cannot be verified; refusing to type blind"
    current = foreground_window_title()
    if _window_identity(expected) != _window_identity(current):
        return f"the foreground window changed (expected a window matching '{expected}', found '{current or '(no foreground window)'}')"
    return None


# -- restoring focus before aborting (Phase 64) -------------------------------
#
# Phase 63 added verify_staged_window: on any mismatch, screen_submit_form
# aborted unconditionally, because eva.desktop.windows.focus_window did not
# reliably work (a bare SetForegroundWindow is blocked by Windows' foreground
# lock from a background process) -- attempting a restore would have been
# pointless. Phase 64 fixed focus_window for real (the AttachThreadInput
# dance), so a mismatch is no longer immediately fatal: it is now worth ONE
# best-effort attempt to bring the staged window back before giving up.
#
# restore_window_focus is kept as its own top-level function -- the same
# pattern as foreground_window_title above -- purely so tests can monkeypatch
# it and never touch a real window, exactly like every other seam in this
# module.


def restore_window_focus(window_title: str) -> None:
    """Best-effort attempt to bring the window matching ``window_title`` back
    to the foreground. Never raises: a failed or impossible restore just means
    the re-verification right after this call will (honestly) still report a
    mismatch, and the caller aborts exactly as it did before this existed.
    """
    try:
        from ..desktop.windows import focus_window

        focus_window(window_title)
    except Exception:
        pass


def ensure_staged_window(staged: "StagedForm") -> str | None:
    """``None`` if the foreground window matches what this form was staged
    against -- restoring focus first if it does not (Phase 64).

    This wraps ``verify_staged_window`` with exactly one recovery attempt: on
    a mismatch, if there is a recorded window to restore to, make one
    best-effort attempt to bring it back to the foreground and check again.
    The abort remains the fallback -- restoring focus makes this usable, it
    must not make it permissive. If the window still does not match after the
    restore attempt (no such window, the restore failed, or a genuinely
    different window is now in front), this returns the fresh mismatch reason
    exactly as if no restore had been attempted: nothing is typed on an
    unconfirmed window. An empty staged title is never restorable (there is
    nothing recorded to restore to), so it is returned unchanged, with no
    restore attempt at all.
    """
    error = verify_staged_window(staged)
    if error is None:
        return None
    expected = str(staged.window_title or "").strip()
    if not expected:
        return error
    restore_window_focus(expected)
    return verify_staged_window(staged)


# -- origin binding: the identity half of the phishing gap (Phase 67) -------
#
# Phase 63/64's window guard above answers "is this still the window I staged
# against" -- but a page can rewrite its own title, and a phishing page can
# simply BE styled and titled to look exactly like the real thing while
# living at a different domain. verify_staged_window cannot see that; it was
# never meant to. This section adds the missing identity check: does the
# CURRENT browser origin (read from the address bar, not the DOM) still
# match the one recorded when the form was staged.
#
# The judgement call this turns on, stated plainly because it is the whole
# point of this phase: a native app (Notepad, an installer, a desktop login)
# has NO origin at all, and "no origin readable" must not silently pass NOR
# blanket-fail -- either would be wrong (silently passing defeats the guard;
# blanket-failing breaks every native-app form fill this project already
# ships). The rule implemented below is:
#
#   (a) The guard BINDS whenever the staged window WAS a browser (StagedForm
#       .is_browser, captured at staging time from the same tree grounding
#       already walks -- see grounding.is_browser_window). Any domain drift
#       for a browser-staged form aborts, whether or not any field declares a
#       required domain -- this is the general phishing defense.
#   (b) Independently, ANY field whose value is a vault reference to an entry
#       that DECLARES a required domain (see vault/store.py's `domain` field)
#       binds too, even in a window that does not look like a browser. A
#       declared-domain entry that cannot read an origin FAILS CLOSED --
#       that is the entire point of declaring one: it must never silently
#       fill on a surface it cannot verify.
#   (c) An undeclared field in a native (non-browser) window is untouched by
#       either rule and behaves exactly as it did before this phase existed.


def foreground_origin() -> tuple[bool, str]:
    """``(is_browser, domain)`` for the CURRENT foreground surface.

    Reads the same accessibility tree grounding already walks (one shared
    enumeration for both facts, not two). Never raises: any failure -- flag
    off, library absent, no browser, unreadable omnibox -- degrades to
    ``(False, "")``, the same "not a browser" case a native app produces
    honestly. Mirrors :func:`foreground_window_title`'s never-fail contract.
    """
    try:
        from .grounding import enumerate_elements, is_browser_window, read_origin

        elements = enumerate_elements()
        browser = is_browser_window(elements)
        origin = read_origin(elements)
        return browser, (origin.domain if origin else "")
    except Exception:
        return False, ""


def _normalize_domain_for_compare(domain: str) -> str:
    """Case-fold and strip a leading "www." so the same site does not
    spuriously mismatch itself. Deliberately NOT a substring/containment
    match -- "mybank.com" must never be satisfied by
    "mybank.com.attacker.example" merely because it appears inside it, the
    way target_verifier's looser UI-observation heuristic works elsewhere in
    this project. This is a security boundary, not a UI hint, so it requires
    exact (normalized) equality; the only cost is an occasional false ABORT
    (www vs bare-domain drift), never a false ACCEPT.
    """
    text = str(domain or "").strip().lower()
    if text.startswith("www."):
        text = text[4:]
    return text


def verify_staged_origin(staged: "StagedForm") -> str | None:
    """``None`` if the browser origin still matches what this form was staged
    against; otherwise a human-readable reason it does not.

    Only applies when the staged window WAS a browser (rule (a) above) -- a
    native app form is untouched. Fails safe in both directions, mirroring
    ``verify_staged_window``: a browser-staged form whose origin could not be
    read AT STAGING TIME (``origin_domain`` empty) is itself unverifiable and
    refused rather than assumed safe, and any domain drift since staging is
    reported and must abort the run.
    """
    if not staged.is_browser:
        return None
    expected = _normalize_domain_for_compare(staged.origin_domain)
    if not expected:
        return (
            "the browser's address bar could not be read when this form was staged, "
            "so its page origin cannot be verified; refusing to type blind"
        )
    _, current_domain = foreground_origin()
    current = _normalize_domain_for_compare(current_domain)
    if not current or current != expected:
        return (
            f"the page origin changed (expected a page on '{staged.origin_domain}', "
            f"found '{current_domain or '(no readable page origin)'}')"
        )
    return None


def verify_declared_domain(required_domain: str) -> str | None:
    """``None`` if the CURRENT browser origin matches ``required_domain`` (a
    vault entry's declared binding, rule (b) above); otherwise a reason it
    does not -- including when no origin can be read at all.

    This is the fail-closed half of the design: a declared-domain entry that
    cannot verify an origin must never fill anyway just because the window
    does not happen to look like a browser (kiosk mode, an unrecognised
    browser, or grounding briefly failing) -- that would defeat the entire
    reason someone declared a domain in the first place.
    """
    required = _normalize_domain_for_compare(required_domain)
    if not required:
        return None
    _, current_domain = foreground_origin()
    current = _normalize_domain_for_compare(current_domain)
    if not current or current != required:
        return (
            f"this saved value is bound to domain '{required_domain}', but the current "
            f"page origin is '{current_domain or 'unreadable'}'"
        )
    return None


def _looks_like_secret(value: str) -> bool:
    try:
        from ..privacy.secrets_broker import contains_secret_leak

        return bool(contains_secret_leak(value))
    except Exception:
        # Fail cautious: if we cannot tell, treat it as sensitive (mask it).
        return True


def _ok(result: object) -> bool:
    return isinstance(result, dict) and result.get("ok") is True


def _error_of(result: object) -> str:
    if isinstance(result, dict):
        return str(result.get("error") or "") + " " + str(result.get("message") or "")
    return ""


def _default_executor() -> Executor:
    from ..tools.registry import ToolRegistry

    registry = ToolRegistry()

    def run(tool: str, **kwargs: Any) -> dict:
        result = registry.run(tool, **kwargs)
        return result if isinstance(result, dict) else {"ok": False, "error": "non_dict_result"}

    return run


def fill_form(
    fields: Sequence[FormField | tuple[str, str]],
    *,
    reason: str,
    executor: Executor | None = None,
) -> FillOutcome:
    """Fill each field in order via gated click+type. Stops at the first failure.

    Returns a value-free :class:`FillOutcome`. ``executor(tool, **kwargs)`` is the
    seam — it defaults to routing through the real ToolRegistry gate, so every
    click and keystroke faces the same permission checks as a typed command.
    """
    run = executor or _default_executor()
    normalized = [f if isinstance(f, FormField) else FormField(str(f[0]), str(f[1])) for f in fields]

    steps: list[FillStep] = []
    filled = 0
    for spec in normalized:
        label = spec.label.strip()
        secret = _looks_like_secret(spec.value)
        if not label:
            steps.append(FillStep("", "not_found", secret, "empty field label"))
            return FillOutcome(steps, filled, False, "a field had no label")

        # 1. Focus the field. The gated tool resolves the label via grounding and
        #    enforces the confidence + real-input gates; we only read its verdict.
        click = run("screen.click", reason=reason, label=label)
        if not _ok(click):
            err = _error_of(click).lower()
            if "ambiguous" in err:
                steps.append(FillStep(label, "ambiguous", secret, _error_of(click).strip()[:200]))
                return FillOutcome(steps, filled, False, f"'{label}' matched several fields; be more specific")
            if "ui_target_not_found" in err or "target_required" in err or "low_confidence" in err:
                steps.append(FillStep(label, "not_found", secret, f"could not find field '{label}' on screen"))
                return FillOutcome(steps, filled, False, f"could not find field '{label}'")
            steps.append(FillStep(label, "click_refused", secret, _error_of(click).strip()[:160]))
            return FillOutcome(steps, filled, False, f"click on '{label}' was refused")

        # 2. Type the value. Never store or return the value itself.
        typed = run("screen.type_text", reason=reason, text=spec.value)
        if not _ok(typed):
            steps.append(FillStep(label, "type_refused", secret, _error_of(typed).strip()[:160]))
            return FillOutcome(steps, filled, False, f"typing into '{label}' was refused")

        steps.append(FillStep(label, "filled", secret))
        filled += 1

    return FillOutcome(steps, filled, True, None)


def parse_form_spec(text: str) -> list[FormField]:
    """Parse ``Email=me@x.com; Password=secret; Full Name=John`` into fields.

    Order-preserving. Labels may contain spaces; the split is on the FIRST '='
    of each ';'-separated clause so values may contain '='. Clauses without an
    '=' are skipped. Values are kept verbatim (only outer whitespace trimmed)."""
    fields: list[FormField] = []
    for clause in str(text or "").split(";"):
        if "=" not in clause:
            continue
        label, value = clause.split("=", 1)
        label = label.strip()
        value = value.strip()
        if label and value:
            fields.append(FormField(label, value))
    return fields


__all__ = [
    "FormField",
    "FillStep",
    "FillOutcome",
    "fill_form",
    "parse_form_spec",
    "VAULT_PREFIX",
    "is_vault_ref",
    "vault_ref_name",
    "SubmitSpec",
    "StagedForm",
    "stage_form",
    "peek_staged_form",
    "pop_staged_form",
    "describe_staged_form",
    "foreground_window_title",
    "verify_staged_window",
    "restore_window_focus",
    "ensure_staged_window",
    "foreground_origin",
    "verify_staged_origin",
    "verify_declared_domain",
]
