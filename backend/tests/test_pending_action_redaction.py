"""Regression tests for sensitive-argument redaction in the pending-action
ledger (see ToolSpec.sensitive_args / ToolRegistry._create_gated_pending).

Confirmed defect: screen.type_text is confirm-class (safety_level='sensitive',
requires_confirmation=True), so every call goes through
ToolRegistry._create_gated_pending, which used to write the RAW call
arguments into the append-only JSONL ledger via payload_summary and
redacted_payload. redact_secrets/sanitize_payload only catch STRUCTURED
secrets (API keys, emails) -- an arbitrary typed password sailed straight
through and landed on disk in plaintext.

The fix masks any argument named in a tool's ToolSpec.sensitive_args to
"[HIDDEN]" before it reaches the ledger, while the real (unmasked) args are
still handed to tool_gate.register_pending_call so run_approved() can
actually perform the action later.

backend/tests/conftest.py's autouse `eva_pending_action_ledger_path` fixture
already redirects EVA_PENDING_ACTION_LEDGER_PATH to a tmp_path file for every
test in this suite, so the real ledger is never touched.
"""

from __future__ import annotations

from eva.permissions.ledger import ledger_path
from eva.security import tool_gate
from eva.tools.registry import ToolRegistry


def test_screen_type_text_secret_never_hits_the_ledger(eva_pending_action_ledger_path):
    """The exact verified regression: a typed password must not be persisted
    to disk in plaintext, anywhere in the raw ledger file."""
    registry = ToolRegistry()

    result = registry.run("screen.type_text", text="hunter2xyz", reason="probe")

    assert result.get("requires_confirmation") is True, f"unexpected result: {result}"
    ledger_file = ledger_path()
    assert ledger_file.exists(), "gated call did not write to the ledger at all"
    raw_text = ledger_file.read_text(encoding="utf-8")

    assert "hunter2xyz" not in raw_text, (
        "the typed secret leaked into the on-disk pending-action ledger: "
        f"{raw_text!r}"
    )


def test_masked_marker_is_present_not_silently_dropped(eva_pending_action_ledger_path):
    """We want to know masking happened, not that the arg vanished entirely."""
    registry = ToolRegistry()

    registry.run("screen.type_text", text="hunter2xyz", reason="probe")

    raw_text = ledger_path().read_text(encoding="utf-8")
    assert "[HIDDEN]" in raw_text, f"expected the masked marker in the ledger: {raw_text!r}"
    # the sibling non-sensitive arg must still be visible, proving this is
    # selective masking rather than the whole payload being wiped
    assert "probe" in raw_text


def test_execution_still_receives_the_real_unmasked_value(eva_pending_action_ledger_path):
    """Pins the thing most likely to be broken later: masking must only
    touch the durable ledger record, never the args tool_gate replays to the
    real executor via run_approved()."""
    registry = ToolRegistry()

    result = registry.run("screen.type_text", text="hunter2xyz", reason="probe")
    pending_id = result.get("pending_id")
    assert pending_id, f"gate result missing pending_id: {result}"

    stored = tool_gate.get_pending_call(pending_id)
    assert stored is not None, "register_pending_call did not persist the call"
    assert stored["args"]["text"] == "hunter2xyz", (
        "register_pending_call must receive the REAL args, not the masked ones "
        f"-- got: {stored['args']}"
    )


def test_tool_without_sensitive_args_is_unaffected(sandbox_dir, eva_pending_action_ledger_path):
    """No behavior change for the 100+ tools that don't declare
    sensitive_args: their args still land in the ledger normally (subject
    only to the pre-existing generic redact_secrets/sanitize_payload pass,
    which is untouched by this fix -- e.g. it independently masks Windows
    user paths, unrelated to sensitive_args)."""
    registry = ToolRegistry()
    target = sandbox_dir / "victim.txt"
    target.write_text("keep me", encoding="utf-8")

    result = registry.run("file.write_text", path=str(target), content="plain marker content", confirmed=True)

    assert result.get("requires_confirmation") is True, f"unexpected result: {result}"
    raw_text = ledger_path().read_text(encoding="utf-8")
    assert "plain marker content" in raw_text, (
        f"file.write_text's content should still be recorded plainly: {raw_text!r}"
    )
    assert "[HIDDEN]" not in raw_text


def test_screen_hotkey_keys_arg_is_masked(eva_pending_action_ledger_path):
    registry = ToolRegistry()

    result = registry.run("screen.hotkey", keys=["ctrl", "shift", "supersecretmarker"], reason="probe")

    assert result.get("requires_confirmation") is True, f"unexpected result: {result}"
    raw_text = ledger_path().read_text(encoding="utf-8")
    assert "supersecretmarker" not in raw_text
    assert "[HIDDEN]" in raw_text

    pending_id = result.get("pending_id")
    stored = tool_gate.get_pending_call(pending_id)
    assert stored["args"]["keys"] == ["ctrl", "shift", "supersecretmarker"], (
        "execution must still receive the real, unmasked keys list"
    )
