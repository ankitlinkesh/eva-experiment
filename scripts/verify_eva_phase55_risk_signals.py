"""Standalone verifier for Phase 55 (argument-aware risk escalation).

Phase 42 learned to REMOVE friction and locked that down on every side, because
removing friction is dangerous. This is the mirror: ADDING friction, which is
always safe, so it is unconditional. It closes the gap the project keeps
re-learning — the gate classifies per-TOOL, blind to the ARGUMENTS, so an
allow-class ``file.list_dir`` will happily enumerate ``~/.ssh`` and a
``file.copy`` treats a write into a system directory like a write into scratch.

What this verifies:

  1. IT ONLY EVER ESCALATES. allow -> confirm -> override, never the reverse; an
     ordinary target changes nothing; hard_block is terminal and untouched. A
     bug in this layer can only ask for MORE confirmation, never less.
  2. IT IS PROPORTIONATE. A sensitive target on a READING action escalates to
     confirm (ask first); on a MUTATING action to override (the strong phrase).
  3. IT IS ARGUMENT-AWARE, NOT TEXT-PARANOID. A non-target action is not
     escalated just because some argument mentions a sensitive-looking word.
  4. IT WORKS END-TO-END AT THE REAL GATE. ``file.list_dir`` of a sensitive
     directory — allow-class, and today auto-running — is parked for
     confirmation, while an ordinary directory still lists.
  5. IT DOMINATES TRUST DE-ESCALATION (Phase 42): escalation runs first, so a
     risk-raised action is never then auto-allowed for prior approvals.

Fully offline: no network, no LLM, no real filesystem writes outside temp.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.permissions import risk_signals
    from backend.eva.permissions.risk_signals import assess_friction, is_sensitive_target
    from backend.eva.security import tool_gate
    from backend.eva.tools.registry import ToolRegistry
    from backend.eva.tools.safe_file_tools import SAFE_ROOT
    from scripts import verify_eva_all

    # 1. The sensitive-target predicate (pure, both separator styles, traversal).
    for sensitive in (
        r"C:\Windows\System32\drivers\etc\hosts",
        "/home/me/.ssh/id_rsa",
        r"C:\Users\me\.aws\credentials",
        "secrets/prod.env",
        r"C:\Users\me\..\..\Windows\System32\x.dll",  # traversal caught textually
    ):
        check(is_sensitive_target(sensitive), f"{sensitive!r} must be recognised as sensitive")
    for ordinary in (r"C:\Users\me\Documents\notes.txt", "/tmp/scratch/out.csv", "just prose", ""):
        check(not is_sensitive_target(ordinary), f"{ordinary!r} must NOT be sensitive")

    # 2. PROPORTIONATE escalation.
    reading = assess_friction(base_decision="allow", action_type="SAFE_LOCAL_READ", args={"path": "/home/me/.ssh/"})
    check(reading.decision == "confirm" and reading.escalated, "reading a sensitive target must escalate allow->confirm")

    mutating = assess_friction(base_decision="confirm", action_type="SAFE_LOCAL_UI", args={"path": r"C:\Windows\System32\x"})
    check(mutating.decision == "override" and mutating.escalated, "mutating a sensitive target must escalate to override")

    at_ceiling = assess_friction(base_decision="override", action_type="DESTRUCTIVE_FILE_ACTION", args={"dst": "/etc/passwd"})
    check(at_ceiling.decision == "override" and not at_ceiling.escalated, "an already-override action stays override")
    check("sensitive_target" in at_ceiling.signals, "the signal must still be recorded even with no class change")

    # 3. IT ONLY EVER ESCALATES — an ordinary target never changes anything.
    for base in ("allow", "confirm", "override"):
        unchanged = assess_friction(
            base_decision=base, action_type="DESTRUCTIVE_FILE_ACTION",
            args={"dst": r"C:\Users\me\Documents\out.txt"},
        )
        check(unchanged.decision == base and not unchanged.escalated, f"an ordinary target must not change a {base} decision")

    terminal = assess_friction(base_decision="hard_block", action_type="SHELL_ACTION", args={"path": "/etc/passwd"})
    check(terminal.decision == "hard_block" and not terminal.escalated, "hard_block is terminal and must never be altered")

    # 4. ARGUMENT-AWARE, NOT TEXT-PARANOID: a non-target action with a
    #    sensitive-looking WORD (no path semantics) is not escalated.
    prose = assess_friction(base_decision="allow", action_type="MCP_TOOL_CALL", args={"note": "my credentials are safe"})
    check(prose.decision == "allow" and not prose.escalated, "a non-target action must not escalate on prose alone")

    # 5. END TO END through the real registry gate.
    tool_gate.reset_pending_calls()
    registry = ToolRegistry()
    gated = registry.run("file.list_dir", path=r"C:\Users\me\.ssh")
    check(
        isinstance(gated, dict) and (gated.get("requires_confirmation") or gated.get("pending_id")),
        f"listing a sensitive directory must be parked for confirmation, got {gated!r}",
    )
    ordinary = registry.run("file.list_dir", path=str(SAFE_ROOT))
    check(
        not (isinstance(ordinary, dict) and ordinary.get("requires_confirmation")),
        "listing an ordinary directory must still run, not gate",
    )
    tool_gate.reset_pending_calls()

    # 6. The wiring is present in the gate hot path, ahead of Phase 42.
    registry_source = (ROOT / "backend" / "eva" / "tools" / "registry.py").read_text(encoding="utf-8")
    check("assess_friction" in registry_source, "registry.run must call assess_friction")
    idx_risk = registry_source.find("assess_friction(")
    idx_trust = registry_source.find("trust_policies_enabled")
    check(0 <= idx_risk < idx_trust, "risk escalation must run BEFORE trust de-escalation so it dominates")

    # 7. Registration.
    name = "verify_eva_phase55_risk_signals.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 55 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 55 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 55 verifier")
    check(hasattr(risk_signals, "assess_friction"), "sanity")

    print(
        "PASS: Phase 55 argument-aware risk escalation -- the mirror of Phase 42. The gate classifies per-TOOL, "
        "blind to the arguments, so this layer reads the actual call and RAISES friction for a sensitive target: "
        "reading one (allow-class file.list_dir of ~/.ssh) escalates to confirm, mutating one escalates to override. "
        "It can ONLY ever escalate -- an ordinary target changes nothing and hard_block is untouched -- so it is "
        "unconditional and fails safe. It is argument-aware, not text-paranoid (prose mentioning 'credentials' does "
        "not escalate), works end-to-end at the real gate (a sensitive listing is parked, an ordinary one runs), and "
        "runs BEFORE Phase 42 trust de-escalation so a risk-raised action is never then auto-allowed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
