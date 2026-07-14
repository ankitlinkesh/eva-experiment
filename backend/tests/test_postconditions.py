"""Executable spec for backend/eva/tools/postconditions.py (Phase 38).

Covers the provenance contract that makes verification-first execution honest:

  * a written file whose content really is on disk is ``independent`` proof;
  * a claimed write whose content is *not* on disk is caught, not trusted;
  * a delete's real post-condition is file-absence, even though the tool's
    declared ``verification_method`` metadata says ``file_exists``;
  * a bare self-reported read only ever earns ``self_reported`` provenance,
    never ``independent``;
  * a screen/UI effect is ``observed`` (not independently verifiable) and
    always carries a remediation string telling the operator to look; and
  * the executor wires all of this through so an allow-class tool call
    attaches a ``verification`` dict without demoting ``ok``.
"""

from __future__ import annotations

from backend.eva.agent.executor import ToolExecutor
from backend.eva.agent.planner import PlannedToolCall
from backend.eva.tools.postconditions import derive_postcondition, verify_tool_effect
from backend.eva.tools.registry import ToolRegistry


def test_file_write_with_matching_content_is_independent_and_verified(tmp_path):
    target = tmp_path / "written.txt"
    target.write_text("hello phase38", encoding="utf-8")

    outcome = verify_tool_effect(
        "file.write_text", "file_contains", {"path": str(target), "content": "hello phase38"}, {"ok": True}
    )

    assert outcome.provenance == "independent"
    assert outcome.independent is True
    assert outcome.verified is True


def test_file_write_with_content_absent_is_independent_but_not_verified(tmp_path):
    target = tmp_path / "written.txt"
    target.write_text("something else entirely", encoding="utf-8")

    outcome = verify_tool_effect(
        "file.write_text", "file_contains", {"path": str(target), "content": "hello phase38"}, {"ok": True}
    )

    assert outcome.independent is True
    assert outcome.verified is False


def test_delete_tool_on_path_that_still_exists_is_not_verified(tmp_path):
    target = tmp_path / "victim.txt"
    target.write_text("still here", encoding="utf-8")

    outcome = verify_tool_effect("file.delete", "file_exists", {"path": str(target)}, {"ok": True})

    assert outcome.method == "file_absent"
    assert outcome.verified is False


def test_delete_tool_on_removed_path_is_verified(tmp_path):
    target = tmp_path / "victim.txt"
    target.write_text("about to go", encoding="utf-8")
    target.unlink()

    outcome = verify_tool_effect("file.delete", "file_exists", {"path": str(target)}, {"ok": True})

    assert outcome.method == "file_absent"
    assert outcome.verified is True


def test_read_tool_success_is_self_reported_not_independent():
    outcome = verify_tool_effect("workspace_status", "command_result_success", {}, {"ok": True})

    assert outcome.provenance == "self_reported"
    assert outcome.verified is True
    assert outcome.independent is False


def test_read_tool_failure_is_self_reported_and_not_verified():
    outcome = verify_tool_effect("workspace_status", "command_result_success", {}, {"ok": False})

    assert outcome.verified is False


def test_screen_tool_is_observed_with_remediation():
    outcome = verify_tool_effect("screen.type_text", "text_field_contains", {"text": "hi", "reason": "eval"}, {"ok": True})

    assert outcome.provenance == "observed"
    assert outcome.independent is False
    assert outcome.remediation


def test_derive_postcondition_for_delete_is_file_absent():
    post = derive_postcondition("file.delete", "file_exists", {"path": "C:/tmp/whatever.txt"})

    assert post.method == "file_absent"


def test_executor_attaches_self_reported_verification_for_workspace_status():
    executor = ToolExecutor(ToolRegistry())
    result = executor.execute(PlannedToolCall(tool="workspace_status", args={}))

    assert result.ok is True
    assert result.verification is not None
    assert result.verification["provenance"] == "self_reported"
