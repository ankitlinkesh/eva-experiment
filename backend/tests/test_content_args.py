"""Phase 65: Phase 55 must escalate on sensitive TARGETS, not on content.

The defect these pin: `_sensitive_targets` passed the ENTIRE argument value to
`is_sensitive_target()` whenever the value contained a path separator anywhere,
so a message whose BODY merely mentioned a system path escalated allow ->
override -- the heaviest friction tier -- for writing a sentence.

The tests that matter most here are NOT the false positives removed but the
true positives PRESERVED. A blunt fix (skip anything prose-shaped) would pass
the first group and quietly destroy the second.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eva.permissions.risk_signals import assess_friction  # noqa: E402
from eva.security import tool_gate  # noqa: E402
from eva.tools.registry import ToolRegistry  # noqa: E402

SENSITIVE = "C:/Windows/System32/drivers/etc/hosts"


def _probe(tool: str, **args) -> tuple[str, bool]:
    """Run a tool's real spec through the real gate + friction assessment."""
    reg = ToolRegistry()
    spec = reg._tools[tool]
    base = tool_gate.classify_tool_call(spec)
    base = str(getattr(base, "decision", base))
    result = assess_friction(
        base_decision=base,
        action_type=str(getattr(spec, "action_type", "") or ""),
        args=args,
        content_args=tuple(getattr(spec, "content_args", ()) or ()),
    )
    return result.decision, result.escalated


# --------------------------------------------------------------------------
# The false positives this phase removes.
# --------------------------------------------------------------------------

def test_message_body_mentioning_a_path_does_not_escalate():
    decision, escalated = _probe("message.prepare", recipient="bob", message=f"I saved it under {SENSITIVE}")
    assert decision == "allow"
    assert escalated is False


def test_research_note_mentioning_a_path_does_not_escalate():
    decision, escalated = _probe("research_save_note", topic="windows", note=f"see {SENSITIVE}", tags="")
    assert decision == "allow"
    assert escalated is False


def test_screen_click_reason_mentioning_a_path_does_not_escalate():
    decision, escalated = _probe("screen.click", reason=f"clicking the {SENSITIVE} shortcut", label="OK")
    assert decision == "allow"
    assert escalated is False


# --------------------------------------------------------------------------
# The true positives that MUST survive. Each pairs a content arg with a
# target arg on the SAME tool, so a blunt "skip prose" fix fails here.
# --------------------------------------------------------------------------

def test_message_recipient_that_is_a_sensitive_path_still_escalates():
    decision, escalated = _probe("message.prepare", recipient=SENSITIVE, message="hello")
    assert escalated is True
    assert decision != "allow"


def test_research_topic_that_is_a_sensitive_path_still_escalates():
    decision, escalated = _probe("research_save_note", topic=SENSITIVE, note="n", tags="")
    assert escalated is True
    assert decision != "allow"


def test_screen_click_label_that_is_a_sensitive_path_still_escalates():
    """`label` feeds grounding.resolve() -- it is a target selector, not content."""
    decision, escalated = _probe("screen.click", reason="ok", label=SENSITIVE)
    assert escalated is True
    assert decision != "allow"


def test_real_path_argument_still_escalates():
    decision, escalated = _probe("file.list_dir", path="C:/Users/HP/.ssh")
    assert escalated is True
    assert decision != "allow"


def test_traceback_still_escalates_because_the_tool_dereferences_it():
    """code_debug_traceback parses paths out of the text and READS them via
    safe_code_read(), so `traceback` is target-bearing and must NOT be declared
    as content. This test exists to stop a future well-meaning change."""
    decision, escalated = _probe("code_debug_traceback", traceback=f'File "{SENSITIVE}", line 0')
    assert escalated is True
    assert decision != "allow"


def test_traversal_still_escalates():
    decision, escalated = _probe("file.list_dir", path="docs/../../../Users/HP/.ssh/id_rsa")
    assert escalated is True


def test_sensitive_path_smuggled_through_an_undeclared_argument_still_escalates():
    """The deliberate catch-all: an odd argument name is not a way around the
    scan. Only names a ToolSpec explicitly declares as content are skipped."""
    result = assess_friction(
        base_decision="allow",
        action_type="SAFE_LOCAL_READ",
        args={"weird_unknown_name": "C:/Users/HP/.ssh/id_rsa"},
        content_args=(),
    )
    assert result.escalated is True


# --------------------------------------------------------------------------
# Trust boundary: content_args LOWERS friction, so it must come only from the
# ToolSpec in source -- never from anything a caller/model can supply.
# --------------------------------------------------------------------------

def test_caller_supplied_content_args_cannot_lower_friction():
    """A model or HTTP client passing content_args= must not exempt anything.

    This deliberately targets a NON-path argument name (`recipient`). Using a
    conventional path key like `path` would prove nothing: the runtime backstop
    in _sensitive_targets refuses to skip those regardless of what content_args
    says, so such a test passes even when the caller CAN override the spec.
    Mutation-testing caught exactly that hole in an earlier version of this test.
    """
    reg = ToolRegistry()
    spec = reg._tools["message.prepare"]
    assert "recipient" not in tuple(spec.content_args), "premise: recipient is not declared content"

    from eva.permissions.risk_signals import _PATH_ARG_KEYS

    assert "recipient" not in _PATH_ARG_KEYS, "premise: the backstop must NOT be what saves us here"

    # Spec-supplied content_args: recipient is scanned, so this escalates.
    baseline = assess_friction(
        base_decision="allow",
        action_type=str(spec.action_type or ""),
        args={"recipient": SENSITIVE, "message": "x"},
        content_args=tuple(spec.content_args),
    )
    assert baseline.escalated is True

    # Now the attack: the CALLER claims recipient is content. registry.run must
    # never let that reach assess_friction.
    result = reg.run("message.prepare", recipient=SENSITIVE, message="x", content_args=("recipient",))
    assert result.get("ok") is not True or result.get("requires_confirmation") is True, (
        "a caller-supplied content_args exempted a real target -- registry.run must "
        "pass spec.content_args only, never anything derived from kwargs"
    )


def test_content_args_is_stripped_from_the_args_the_tool_receives():
    reg = ToolRegistry()
    spec = reg._tools["file.list_dir"]
    assert "content_args" not in (spec.args_schema or {}).get("properties", {})


def test_a_path_argument_name_is_never_exempt_even_if_declared_content():
    """Runtime backstop for a mis-declared ToolSpec: conventional path argument
    names are scanned regardless of what content_args claims."""
    result = assess_friction(
        base_decision="allow",
        action_type="SAFE_LOCAL_READ",
        args={"path": "C:/Users/HP/.ssh/id_rsa"},
        content_args=("path",),
    )
    assert result.escalated is True


def test_hard_block_is_never_touched_by_content_args():
    result = assess_friction(
        base_decision="hard_block",
        action_type="CREDENTIAL_ACCESS",
        args={"message": "anything"},
        content_args=("message",),
    )
    assert result.decision == "hard_block"
    assert result.escalated is False


def test_content_args_only_ever_removes_escalation_never_adds_one():
    """Declaring content must never make something MORE dangerous."""
    args = {"message": "totally benign text"}
    without = assess_friction(base_decision="allow", action_type="SAFE_LOCAL_UI", args=args, content_args=())
    with_ = assess_friction(base_decision="allow", action_type="SAFE_LOCAL_UI", args=args, content_args=("message",))
    order = {"allow": 0, "confirm": 1, "override": 2, "hard_block": 3}
    assert order[with_.decision] <= order[without.decision]


# --------------------------------------------------------------------------
# Same family as Phase 64: stop claiming verification that never happened.
# --------------------------------------------------------------------------

def test_message_prepare_does_not_claim_it_verified_anything():
    from eva.tools.message_tools import message_prepare

    result = message_prepare("bob", "hello")
    assert result["draft_prepared"] is True
    assert "verification" not in result, (
        "message_prepare used to hardcode verification={'verified': True, "
        "'confidence': 0.8} for merely stashing a dict in memory"
    )
