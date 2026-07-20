"""Standalone verifier for Phase 74 (bounded command runner).

The roadmap item was "native shell". `ActionType.SHELL_ACTION` is hard-blocked
in BOTH gates -- permission_gate.py returns hard_block with "Arbitrary shell
execution is blocked by default", and tool_gate.py refuses it before anything
else -- so the tempting way to deliver a shell is to relax that. This phase does
not, and the first thing verified here is that it did not: the hard block is
asserted still standing, because a phase that quietly loosened it would look
identical from the outside to one that added a safe runner.

What is added instead is not a shell:

  1. THE ARBITRARY-SHELL BLOCK IS INTACT. A SHELL_ACTION tool still classifies
     hard_block, and the new tool is NOT SHELL_ACTION.
  2. NO SHELL INTERPRETER. Structural check that the module never sets
     shell=True and never calls os.system, so `;`, `|`, `&&` and globs reach
     the program as literal argv entries.
  3. A FIXED EXECUTABLE ALLOWLIST -- an unlisted program cannot be named.
  4. READ-ONLY SUBCOMMANDS -- a bounded run cannot mutate the repository.
  5. DANGEROUS FLAGS REFUSED. The failure an executable allowlist alone would
     miss: `git -c core.pager=...`, `--ext-diff`, `--exec-path`,
     `--upload-pack` each turn an allowlisted binary into a launcher.
  6. IT IS NOT PLANNER-VISIBLE, so untrusted content cannot choose to run a
     command at all.
  7. EVERY ROLE IS RED ON IT. Phase 72 fails closed by construction, so a
     newly registered tool is denied to every delegated sub-task without
     anyone having to remember to deny it.
  8. THE GATE STILL SEES IT. The tool is override-class, and the console path
     goes THROUGH registry.run rather than around it.
  9. OUTPUT IS UNTRUSTED. A branch name or commit message can say anything.

Fully offline: `validate` is pure, and the only commands actually executed are
read-only inspections of this repository.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from eva.agents.role_policy import RoleTier, known_roles, tier_for
    from eva.security import tool_gate
    from eva.security.action_types import ActionType
    from eva.shell import bounded_runner
    from eva.shell.bounded_runner import ALLOWED_COMMANDS, describe_allowed, run_bounded, validate
    from eva.tools.registry import ToolRegistry

    TOOL = "shell.run_bounded"

    # ------------------------------------------------------------------ 1
    # The arbitrary-shell hard block is still standing. This is the property a
    # careless "native shell" phase would have traded away.
    class _ShellSpec:
        action_type = ActionType.SHELL_ACTION.value
        safety_level = "dangerous"
        risk_categories = (ActionType.SHELL_ACTION.value,)
        requires_confirmation = True

    check(
        tool_gate.classify_tool_call(_ShellSpec()) == "hard_block",
        "REGRESSION: arbitrary shell execution is no longer hard-blocked",
    )

    registry = ToolRegistry()
    check(TOOL in registry._tools, f"{TOOL} is not registered")
    spec = registry._tools[TOOL]
    check(
        str(spec.action_type) != ActionType.SHELL_ACTION.value,
        "the bounded runner declares SHELL_ACTION; it would be hard-blocked and is not arbitrary shell anyway",
    )

    # ------------------------------------------------------------------ 2
    source = inspect.getsource(bounded_runner)
    check("shell=True" not in source, "the bounded runner enables a shell interpreter")
    check("os.system" not in source, "the bounded runner calls os.system")
    check("shell=False" in source, "the bounded runner does not explicitly disable the shell")

    # ------------------------------------------------------------------ 3/4/5
    for program in ("bash", "sh", "cmd", "powershell", "curl", "rm"):
        check(validate(program, ("--version",)) is not None, f"unlisted program `{program}` was permitted")
    for args in (("push",), ("commit", "-m", "x"), ("reset", "--hard"), ("clean", "-fd")):
        check(validate("git", args) is not None, f"mutating git subcommand permitted: {args}")
    for args in (
        ("status", "-c", "core.pager=calc.exe"),
        ("-c", "core.pager=calc.exe", "status"),
        ("diff", "--ext-diff"),
        ("status", "--exec-path=/tmp"),
        ("status", "--upload-pack=calc.exe"),
    ):
        check(validate("git", args) is not None, f"a flag that launches another program was permitted: {args}")
    for meta in (";", "|", "&", "$", "`", ">", "<"):
        check(validate("git", ("status", f"a{meta}b")) is not None, f"shell metacharacter `{meta}` permitted")
    check(validate("python", ("-c", "import os")) is not None, "python -c was permitted")
    check(validate("pip", ("install", "x")) is not None, "pip install was permitted")

    # ... and the permitted set genuinely works, so this is not merely a
    # runner that refuses everything.
    check(validate("git", ("status",)) is None, "git status was refused")
    result = run_bounded("git", ("status", "--short"))
    check(result.ok is True, f"a permitted read-only command failed: {result.error}")
    check(result.exit_code == 0, "a permitted command returned a non-zero exit code")

    # ------------------------------------------------------------------ 6
    planner_visible = {item["name"] for item in registry.planner_specs()}
    check(TOOL not in planner_visible, f"{TOOL} is planner-visible; untrusted content could choose to run commands")

    # ------------------------------------------------------------------ 7
    for role in known_roles():
        check(
            tier_for(role, TOOL) is RoleTier.RED,
            f"role `{role}` may call {TOOL}; a delegated sub-task must not run commands",
        )

    # ------------------------------------------------------------------ 8
    decision = tool_gate.classify_tool_call(spec)
    check(decision == "override", f"{TOOL} classifies as {decision}, expected override")
    # Pin the DECLARED attributes, not only the resulting decision. Either one
    # alone forces override, so checking the decision cannot see a downgrade of
    # just one of them -- and a tool that reads SAFE_LOCAL_READ is treated as
    # safe by layers that never consult the gate. Found by a mutation that
    # correctly passed: it changed action_type only, and the decision was still
    # override because safety_level carried it.
    check(
        str(spec.action_type) == "SYSTEM_CHANGE",
        f"{TOOL} declares action_type={spec.action_type}; command execution must not read as a safe action type",
    )
    check(
        str(spec.safety_level) == "dangerous",
        f"{TOOL} declares safety_level={spec.safety_level}; expected dangerous",
    )
    # The console path goes THROUGH the gate. If it called run_bounded directly
    # it would work and would also establish the console as a way around the
    # gate -- the property that must not exist.
    from eva.core import fast_command_shell

    console_source = inspect.getsource(fast_command_shell)
    check('tools.run("shell.run_bounded"' in console_source, "the console path does not go through registry.run")

    # ------------------------------------------------------------------ 9
    check(result.untrusted is True, "command output is not marked untrusted")
    rendered = result.as_text()
    check("untrusted" in rendered.lower(), "rendered output dropped the untrusted marker")
    check("not an instruction" in rendered.lower(), "rendered output does not say output is not an instruction")

    # Refused input runs nothing at all.
    refused = run_bounded("git", ("push",))
    check(refused.refused is True, "a refused command was not marked as refused")
    check(refused.exit_code is None, "a refused command still produced an exit code -- it may have run")

    check(describe_allowed(), "sanity")
    check(ALLOWED_COMMANDS, "sanity")

    # ------------------------------------------------------------------ 10
    import verify_eva_all

    name = "verify_eva_phase74_bounded_runner.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 74 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 74 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 74 verifier")

    print(
        "PASS: Phase 74 bounded command runner -- and, first, arbitrary shell execution is STILL hard-blocked in the "
        "gate, which is the property a careless 'native shell' phase would have traded away. What was added is not a "
        "shell: subprocess is called with an argument list and shell=False (asserted structurally), so `;`, `|`, `&&` "
        "and globs reach the program as literal argv entries; the executable allowlist is fixed in source, so an "
        "unlisted program cannot be named; subcommands are read-only, so a bounded run cannot mutate the repository; "
        "and dangerous flags are refused -- the failure an executable allowlist ALONE would miss, since `git -c "
        "core.pager=...`, `--ext-diff`, `--exec-path` and `--upload-pack` each turn an allowlisted binary into a "
        "launcher for something else. The tool is override-class and not planner-visible, so untrusted content cannot "
        "choose to run a command; every delegated role is RED on it automatically because Phase 72 fails closed by "
        "construction; and the console path goes THROUGH registry.run rather than around it, so the gate stays "
        "meaningful. Output is marked untrusted, because a branch name or a commit message can say anything."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
