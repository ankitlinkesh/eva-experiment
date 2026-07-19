"""Executable spec for backend/eva/agent/verifier.py (Phase 69).

Confirmed defect: verify_action had its own, second copy of the exact
self-report-laundering bug Phase 64 fixed in tools/postconditions.py --
for every method except file_exists/file_contains it did
``ok = bool(observation.success)`` and dressed that up as a 0.65/0.75/0.8-
confidence "verification", i.e. it trusted the actor's own claim of success
and called that proof. It was dormant (only two callers, both of which use
the already-honest file_contains path) until Phase 72 arms it via agents/.

The fix delegates to tools.postconditions.verify_tool_effect (the same
machinery agent/executor.py already uses for the real ToolRegistry path)
instead of re-implementing the honesty rules a second time. These tests pin:

  * every method that used to launder self-report now honestly reports
    verified=False, provenance="unverified" -- even when observation.success
    is True;
  * file_contains still verifies independently against real disk content
    (unchanged, still the honest path);
  * a failed observation (success=False) never reads as verified=True for
    the command_result_success fallback;
  * safe_file_tools.file_write_text (the one real, non-test caller of
    verify_action today) still succeeds on a genuine write and still rolls
    back a genuine verification failure -- the exact regression this phase
    warns against.
"""

from __future__ import annotations

from backend.eva.agent.action_model import AgentAction, AgentObservation
from backend.eva.agent.verifier import verify_action
from backend.eva.tools import safe_file_tools


def _action(method: str, **verification_extra) -> AgentAction:
    return AgentAction(
        tool_name="screen.type_text",
        action_type="ALLOW_CLASS",
        description="probe",
        params={"text": "hi"},
        verification={"method": method, **verification_extra},
    )


def test_previously_laundering_methods_no_longer_trust_the_self_report():
    """The core Phase 69 regression pin: for every method that used to do
    ok = bool(observation.success), a self-reported success=True must NOT
    produce verified=True any more -- nothing here can independently check
    any of these, so they must honestly come back unverified."""
    for method in (
        "app_window_active",
        "url_opened",
        "screen_state_changed",
        "message_draft_prepared",
        "message_sent_likely",
        "text_field_contains",
    ):
        action = _action(method)
        observation = AgentObservation(action.action_id, True, {}, "claimed success")

        result = verify_action(action, observation)

        assert result.verified is False, f"{method}: must not launder observation.success=True into verified=True"
        assert result.provenance == "unverified", f"{method}: expected unverified provenance, got {result.provenance!r}"
        assert result.independent is False, f"{method}: must not claim independent"


def test_default_fallback_method_no_longer_claims_unlabeled_flat_confidence():
    """The bare `else` branch (no recognized method) used to be
    ok = bool(observation.success) at a flat, unlabeled confidence of 0.8 --
    no provenance concept existed at all. derive_postcondition treats an
    unrecognized method as command_result_success (Phase 64's own rule: that
    one fallback legitimately trusts a self-report), so this must now be
    explicitly labeled self_reported at self_reported's honest confidence
    (0.6), never independent and never the old flat 0.8."""
    action = _action("some_totally_unknown_method")
    observation = AgentObservation(action.action_id, True, {}, "claimed success")

    result = verify_action(action, observation)

    assert result.provenance == "self_reported"
    assert result.independent is False
    assert result.confidence == 0.6, f"must not keep the old unlabeled flat 0.8 confidence: {result.confidence}"


def test_command_result_success_is_self_reported_not_independent_and_honors_failure():
    """command_result_success is the one fallback method that legitimately
    trusts a self-report (Phase 64's own rule) -- but it must be LABELED as
    self_reported, never independent, and a False self-report must produce
    verified=False, never read as success."""
    action = AgentAction(
        tool_name="workspace_status",
        action_type="ALLOW_CLASS",
        description="probe",
        params={},
        verification={"method": "command_result_success"},
    )

    ok_observation = AgentObservation(action.action_id, True, {}, "ok")
    ok_result = verify_action(action, ok_observation)
    assert ok_result.verified is True
    assert ok_result.provenance == "self_reported"
    assert ok_result.independent is False

    failed_observation = AgentObservation(action.action_id, False, {}, "it broke", error="boom")
    failed_result = verify_action(action, failed_observation)
    assert failed_result.verified is False, (
        "a failed observation (success=False) must never read as verified=True -- "
        f"got {failed_result.as_dict()}"
    )

    # Isolate the observation.success -> result "ok" mapping itself, with no
    # error string present to fall back on: _result_reports_success's
    # `if result.get("error")` branch would rescue a broken `ok` mapping and
    # mask the exact regression this phase is about, so this case must not
    # carry an error message.
    failed_no_error_observation = AgentObservation(action.action_id, False, {}, "it broke silently")
    failed_no_error_result = verify_action(action, failed_no_error_observation)
    assert failed_no_error_result.verified is False, (
        "observation.success=False with no error string must still map to a falsy result -- "
        f"got {failed_no_error_result.as_dict()}"
    )


def test_file_contains_still_verifies_independently_against_real_disk_content(tmp_path):
    """The one method that was already honest pre-Phase-69 must be unchanged
    behaviorally: it reads the real file, not the observation."""
    target = tmp_path / "note.txt"
    target.write_text("hello phase69", encoding="utf-8")

    action = AgentAction(
        tool_name="file.write_text",
        action_type="DESTRUCTIVE_FILE_ACTION",
        description="write",
        params={"path": str(target), "content": "hello phase69"},
        verification={"method": "file_contains", "path": str(target), "text": "hello phase69"},
    )
    # Even a self-reported FAILURE must not stop the independent disk check
    # from finding the real content and reporting verified=True.
    lying_failure_observation = AgentObservation(action.action_id, False, {}, "claimed failure", error="lied")

    result = verify_action(action, lying_failure_observation)

    assert result.verified is True, f"file_contains must check real disk content independent of the self-report: {result.as_dict()}"
    assert result.provenance == "independent"
    assert result.independent is True


def test_verification_text_takes_precedence_over_params_content(tmp_path):
    """action.verification currently takes precedence over action.params for
    path/text (see the pre-Phase-69 file_exists/file_contains branches) --
    this must be preserved through the delegation. Give params["content"] a
    value that is NOT on disk and verification["text"] a value that IS, so
    the two disagree and only the correct precedence passes."""
    target = tmp_path / "note.txt"
    target.write_text("the real text", encoding="utf-8")

    action = AgentAction(
        tool_name="file.write_text",
        action_type="DESTRUCTIVE_FILE_ACTION",
        description="write",
        params={"path": str(target), "content": "stale text nobody wrote"},
        verification={"method": "file_contains", "path": str(target), "text": "the real text"},
    )
    observation = AgentObservation(action.action_id, True, {}, "claimed success")

    result = verify_action(action, observation)

    assert result.verified is True, (
        f"verification['text'] must take precedence over params['content']: {result.as_dict()}"
    )


def test_file_contains_fails_when_content_genuinely_absent(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("something else", encoding="utf-8")

    action = AgentAction(
        tool_name="file.write_text",
        action_type="DESTRUCTIVE_FILE_ACTION",
        description="write",
        params={"path": str(target), "content": "hello phase69"},
        verification={"method": "file_contains", "path": str(target), "text": "hello phase69"},
    )
    observation = AgentObservation(action.action_id, True, {}, "claimed success")

    result = verify_action(action, observation)

    assert result.verified is False
    assert result.independent is True


def test_verify_action_is_fail_safe_and_never_raises():
    """Malformed action/observation input must never raise into the caller."""
    action = AgentAction(tool_name="whatever", action_type="ALLOW_CLASS", description="", params=None or {}, verification={"method": "file_exists"})
    observation = AgentObservation(action.action_id, True, {}, "ok")

    result = verify_action(action, observation)  # must not raise
    assert result.action_id == action.action_id


# -- The one real (non-test) caller: safe_file_tools.file_write_text --------


def test_file_write_text_succeeds_on_a_real_write(sandbox_dir):
    target = sandbox_dir / "phase69_real_write.txt"

    result = safe_file_tools.file_write_text(str(target), "written for real")

    assert result["ok"] is True, result
    assert target.read_text(encoding="utf-8") == "written for real"
    assert result["verification"]["verified"] is True
    assert result["verification"]["provenance"] == "independent"


def test_file_write_text_rolls_back_on_genuine_verification_failure(sandbox_dir, monkeypatch):
    """The exact regression this phase warns against: if delegation were
    wired wrong, a successful write could start reading as unverified (or a
    failed write could start reading as verified), either of which would
    stop file_write_text's existing rollback-on-failure logic from doing its
    job. Force a genuine verification failure by having the write land
    different content than what verification will check for (simulating a
    write that silently didn't take), and confirm the rollback still fires."""
    target = sandbox_dir / "phase69_rollback.txt"
    target.write_text("original content", encoding="utf-8")

    import backend.eva.tools.safe_file_tools as sft_module

    real_write_text = __import__("pathlib").Path.write_text

    def _lying_write_text(self, data, *args, **kwargs):
        # Pretend to write "after" but actually leave old content on disk --
        # simulates a write that silently failed to take effect.
        return real_write_text(self, "original content", *args, **kwargs)

    monkeypatch.setattr(__import__("pathlib").Path, "write_text", _lying_write_text)

    result = sft_module.file_write_text(str(target), "after")

    assert result["ok"] is False, f"a genuine verification failure must not report ok=True: {result}"
    assert result["verification"]["verified"] is False
    assert result["rollback"]["success"] is True
    assert target.read_text(encoding="utf-8") == "original content", "rollback must restore the checkpointed content"
