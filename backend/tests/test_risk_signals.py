"""Argument-aware risk escalation (Phase 55).

The gate classifies per-tool, blind to where an action points. This layer reads
the arguments and raises friction for a sensitive target. Every test here is
really one property: it can only ever ADD friction, proportionately, and it does
so end-to-end through the real registry gate.
"""

from __future__ import annotations

from eva.permissions.risk_signals import FrictionAssessment, assess_friction, is_sensitive_target
from eva.security import tool_gate
from eva.tools.registry import ToolRegistry


# -- the sensitive-target predicate ----------------------------------------

def test_sensitive_paths_are_recognised_both_separator_styles():
    assert is_sensitive_target(r"C:\Windows\System32\drivers\etc\hosts")
    assert is_sensitive_target("/home/me/.ssh/id_rsa")
    assert is_sensitive_target(r"C:\Users\me\.aws\credentials")
    assert is_sensitive_target("secrets/prod.env")


def test_traversal_toward_a_system_dir_is_still_caught_textually():
    # No filesystem resolution: the literal marker is present in the text.
    assert is_sensitive_target(r"C:\Users\me\..\..\Windows\System32\x.dll")


def test_ordinary_paths_are_not_sensitive():
    assert not is_sensitive_target(r"C:\Users\me\Documents\notes.txt")
    assert not is_sensitive_target("/tmp/scratch/output.csv")
    assert not is_sensitive_target("just some prose about my day")
    assert not is_sensitive_target("")


# -- proportionate escalation ----------------------------------------------

def test_reading_a_sensitive_target_escalates_allow_to_confirm():
    a = assess_friction(base_decision="allow", action_type="SAFE_LOCAL_READ", args={"path": "/home/me/.ssh/"})
    assert a.decision == "confirm"
    assert a.escalated is True
    assert "sensitive_target" in a.signals


def test_mutating_a_sensitive_target_escalates_to_override():
    a = assess_friction(base_decision="confirm", action_type="SAFE_LOCAL_UI", args={"path": r"C:\Windows\System32\x.dll"})
    assert a.decision == "override"
    assert a.escalated is True


def test_a_destructive_action_on_a_sensitive_target_stays_override_but_records_signal():
    a = assess_friction(base_decision="override", action_type="DESTRUCTIVE_FILE_ACTION", args={"dst": "/etc/passwd"})
    assert a.decision == "override"
    assert a.escalated is False          # already at the ceiling
    assert "sensitive_target" in a.signals  # ...but the signal is still recorded


# -- it NEVER lowers friction ----------------------------------------------

def test_ordinary_target_never_changes_anything():
    for base in ("allow", "confirm", "override"):
        a = assess_friction(base_decision=base, action_type="DESTRUCTIVE_FILE_ACTION", args={"dst": r"C:\Users\me\scratch\out.txt"})
        assert a.decision == base
        assert a.escalated is False


def test_hard_block_is_terminal_and_untouched():
    a = assess_friction(base_decision="hard_block", action_type="SHELL_ACTION", args={"path": "/etc/passwd"})
    assert a.decision == "hard_block"
    assert a.escalated is False


def test_allow_class_status_tool_with_no_path_is_untouched():
    a = assess_friction(base_decision="allow", action_type="SAFE_LOCAL_READ", args={"query": "how are you"})
    assert a.decision == "allow"
    assert a.escalated is False


def test_sensitive_string_in_a_non_target_action_does_not_escalate():
    # An allow-class action that does NOT act on a target must not be escalated
    # just because some argument text mentions a sensitive-looking word.
    a = assess_friction(base_decision="allow", action_type="MCP_TOOL_CALL", args={"note": "my credentials are safe"})
    assert a.decision == "allow"
    assert a.escalated is False


# -- end to end through the real gate --------------------------------------

def test_list_dir_of_a_sensitive_directory_is_gated_at_the_registry(tmp_path):
    """file.list_dir is allow-class, so listing ~/.ssh would auto-run. The risk
    layer must park it for confirmation instead of returning contents."""
    tool_gate.reset_pending_calls()
    registry = ToolRegistry()
    result = registry.run("file.list_dir", path=r"C:\Users\me\.ssh")
    assert isinstance(result, dict)
    assert result.get("requires_confirmation") or result.get("pending_id"), result
    tool_gate.reset_pending_calls()


def test_list_dir_of_an_ordinary_directory_still_runs():
    """An ordinary directory (inside the sandbox roots) is unaffected by the risk
    layer: it runs and returns a listing, not a confirmation stub."""
    from eva.tools.safe_file_tools import SAFE_ROOT

    tool_gate.reset_pending_calls()
    registry = ToolRegistry()
    result = registry.run("file.list_dir", path=str(SAFE_ROOT))
    assert not (isinstance(result, dict) and result.get("requires_confirmation")), result
    tool_gate.reset_pending_calls()


def test_the_assessment_is_a_frozen_value():
    a = assess_friction(base_decision="allow", action_type="SAFE_LOCAL_READ", args={"path": "/x/.ssh/id_rsa"})
    assert isinstance(a, FrictionAssessment)
    assert isinstance(a.as_dict(), dict)
