"""Standalone verifier for Phase 75 (isolated action explainer).

Every gate in this project ends at the same place: a person deciding whether to
approve. If that person is shown a tool name and an argument dict they cannot
read, they will approve on trust, and every gate above becomes decoration. This
phase makes the approval prompt legible without making it manipulable.

What this verifies:

  1. THE DETERMINISTIC HALF IS ALWAYS PRESENT AND MODEL-FREE. Assembled from
     the ToolSpec's own description and declared action_type, so nothing can
     talk it into saying something false, and an approval stays reviewable when
     every LLM provider is down.
  2. THE VERBATIM CALL IS ALWAYS SHOWN. The action being explained is untrusted
     input -- a planner steered by hostile content can produce a call crafted
     to read innocently -- so the raw call anchors the prompt and a generated
     sentence never replaces it.
  3. THE GENERATED HALF IS ISOLATED. Called with `tools=None`, so it cannot
     act, and with a message list rebuilt from the deterministic fields alone,
     so nothing said earlier in a conversation can shape how an action is
     described at the moment of approval.
  4. SECRETS STAY MASKED. The explanation renders the ledger's redacted
     payload; it must not become the thing that prints what masking hid.
  5. THE APPROVAL PROMPT ACTUALLY CARRIES IT, end to end through the real gate.
  6. THE CONSOLE ENTRY DOES NOT SHADOW ITS NEIGHBOURS. `explain` is claimed
     only for a pending-action id, because `explain feature ...` and
     `explain project architecture` are matched LATER in the ordered dispatcher
     and an earlier branch would silently capture both (Phase 71).

Fully offline: no model is called. The generated path is exercised only through
its failure mode, which is itself the property being checked.
"""

from __future__ import annotations

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
    from eva.agents.explainer import explain_action
    from eva.core.fast_commands import maybe_handle_fast_command
    from eva.security.action_types import ActionType
    from eva.tools.registry import ToolRegistry

    # ------------------------------------------------------------------ 1
    explanation = explain_action(
        tool="file.delete",
        description="Delete a file.",
        action_type="DESTRUCTIVE_FILE_ACTION",
        decision="override",
        args={"path": "notes.txt"},
    )
    check(explanation.generated is None, "the deterministic half invoked a model")
    check("Delete a file." in explanation.what_it_does, "the tool's own description is missing")
    check("will not run" in explanation.if_declined, "the prompt does not say what happens if declined")
    check("override" in explanation.approval_meaning.lower(), "the override tier is not explained")

    # Every declared action type must produce readable text -- a new one must
    # not silently yield a blank "why".
    for action_type in (item.value for item in ActionType):
        text = explain_action("t", "d", action_type, "confirm").why_gated
        check(text.strip() and action_type in text, f"no plain-language explanation for {action_type}")

    # ------------------------------------------------------------------ 2
    check("file.delete" in explanation.command_line, "the verbatim call is missing the tool name")
    check("notes.txt" in explanation.command_line, "the verbatim call is missing its arguments")
    check("file.delete" in explanation.as_text(), "the rendered prompt does not show the call")

    # ------------------------------------------------------------------ 3
    import inspect

    from eva.agents import explainer

    source = inspect.getsource(explainer)
    # Checked by AST, not by substring: an earlier version of this verifier
    # tested `"tools=None" in source` and PASSED against a build where the call
    # said `tools=[]`, because that exact string also appears in this module's
    # own docstring. A check that a docstring can satisfy is not a check.
    import ast

    tree = ast.parse(source)
    tools_args = [
        keyword.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "complete_with_fallback"
        for keyword in node.keywords
        if keyword.arg == "tools"
    ]
    check(tools_args, "the explainer's model call does not pass `tools` at all")
    check(
        all(isinstance(value, ast.Constant) and value.value is None for value in tools_args),
        "the explainer's model call passes a non-None `tools`; it could act",
    )
    # `generate_explanation` takes ONE argument, the explanation itself. If it
    # ever grew a context/history/session parameter, the isolation claim would
    # be false while every test above still passed, so the signature is pinned.
    signature = inspect.signature(explainer.generate_explanation)
    check(
        list(signature.parameters) == ["explanation"],
        f"generate_explanation accepts {list(signature.parameters)}; it must receive only the action, never context",
    )
    # The prompt is rebuilt from the deterministic fields; no caller context.
    check(
        'f"Action: {explanation.command_line}"' in source,
        "the generated prompt is not rebuilt from the deterministic fields",
    )

    # ------------------------------------------------------------------ 4
    masked = explain_action("screen.type_text", "Type text.", "SAFE_LOCAL_UI", "confirm", {"text": "[HIDDEN]"})
    check("[HIDDEN]" in masked.command_line, "the explanation did not render the masked payload")

    # ------------------------------------------------------------------ 5
    # End to end through the real gate: an override-class call must come back
    # with an explanation attached, not just a tool name.
    registry = ToolRegistry()
    parked = registry.run("shell.run_bounded", command="git", args=["status"])
    check(isinstance(parked, dict) and parked.get("requires_confirmation"), "the gate did not park an override-class call")
    check(parked.get("explanation"), "a parked action carries no explanation")
    message = str(parked.get("message") or "")
    check("What you are being asked to approve" in message, "the approval prompt does not carry the explanation")
    check("shell.run_bounded" in message, "the approval prompt does not show the call")
    check("explain " in message, "the approval prompt does not offer the `explain` follow-up")

    # ------------------------------------------------------------------ 6
    # Shadowing: the later branches must keep their meaning.
    tools = ToolRegistry()
    feature = maybe_handle_fast_command("explain feature vault", tools, session_context={}, memory=None, session_id="v75")
    check(feature is not None, "`explain feature ...` stopped being handled")
    check(
        "What you are being asked to approve" not in feature[0],
        "`explain feature ...` was captured by the pending-action explainer",
    )
    architecture = maybe_handle_fast_command(
        "explain project architecture", tools, session_context={}, memory=None, session_id="v75"
    )
    check(architecture is not None, "`explain project architecture` stopped being handled")
    check(
        "What you are being asked to approve" not in architecture[0],
        "`explain project architecture` was captured by the pending-action explainer",
    )
    missing = maybe_handle_fast_command("explain act_nope", tools, session_context={}, memory=None, session_id="v75")
    check(missing is not None and "No pending action" in missing[0], "an unknown pending id was not reported")

    # ------------------------------------------------------------------ 7
    import verify_eva_all

    name = "verify_eva_phase75_explainer.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 75 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 75 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 75 verifier")

    print(
        "PASS: Phase 75 isolated action explainer. Every gate in this project ends at a person deciding whether to "
        "approve, and a prompt showing only a tool name and an argument dict gets approved on trust. The approval "
        "prompt now carries a DETERMINISTIC explanation assembled from source of truth -- the tool's own description "
        "and declared action_type -- with no model involved, so nothing can talk it into saying something false and "
        "an action stays reviewable when every provider is down. The verbatim call is always shown, because the "
        "action being explained is untrusted input and a generated sentence must never replace it. The optional "
        "generated half is isolated: `tools=None` so it cannot act, and a prompt rebuilt from the deterministic "
        "fields alone so nothing said earlier in a conversation can shape how an action is described at the moment "
        "of approval; it is on request (`explain <id>`) rather than automatic, because explaining every gated action "
        "would spend a 20/min budget on prompts already read. Secrets stay masked -- the explanation renders the "
        "ledger's redacted payload and never becomes the thing that prints what masking hid. And the console entry "
        "claims `explain` only for a pending-action id, so the later `explain feature ...` and `explain project "
        "architecture` branches keep their meaning."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
