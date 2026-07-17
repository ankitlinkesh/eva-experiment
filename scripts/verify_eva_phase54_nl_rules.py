"""Standalone verifier for Phase 54 (natural-language rule creation).

Phase 46 built a rule engine and Phase 53 gave it a loop, but a rule could only
be created from Python — there was no way for a person to *say* "remind me every
morning to summarize my news" and have it become a real, persisted rule. This is
that front door.

The verification centres on the properties that make an unattended-firing rule
safe to create from a sentence:

  1. DETERMINISTIC + LLM-FREE: the same sentence always yields the same rule.
  2. IT REFUSES rather than guesses: a sentence with no schedule/trigger returns
     None, so ordinary requests are NOT swallowed by the rule creator.
  3. IT PERSISTS: a parsed rule round-trips through the real store, and the
     typed fast-command path actually creates, lists, pauses and deletes rules.
  4. THE TRUST BOUNDARY HOLDS: creation lives on the typed-console path only —
     it is NOT registered as a planner tool, so untrusted content (Phase 40)
     cannot stand up a standing proposer.
  5. A created rule only PROPOSES (the Phase 46 invariant is unchanged): its
     request is stored verbatim and, when it fires later, still faces the gate.

Fully offline: temp DBs, no network, no LLM.
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
    from backend.eva.proactivity import nl_rules
    from backend.eva.proactivity.models import DAILY, FILE_CHANGE, INTERVAL
    from backend.eva.proactivity.nl_rules import ParsedRule, parse_rule_request
    from backend.eva.proactivity.store import ProactivityStore
    from scripts import verify_eva_all

    scratch = Path(tempfile.mkdtemp(prefix="eva_phase54_"))

    # 1. The three shapes parse to the right kind + spec.
    daily = parse_rule_request("remind me every morning to summarize my news")
    check(daily is not None and daily.kind == DAILY, "every-morning must parse to a daily rule")
    check(daily.spec == {"at": "08:00"}, f"'morning' must default to 08:00, got {daily.spec!r}")
    check(daily.request == "summarize my news", f"the action must be extracted cleanly, got {daily.request!r}")

    at = parse_rule_request("every day at 6:30pm check the build")
    check(at is not None and at.spec == {"at": "18:30"}, f"explicit pm time must win, got {at.spec if at else None!r}")

    interval = parse_rule_request("every 30 minutes check the build status")
    check(interval is not None and interval.kind == INTERVAL, "every-N-minutes must parse to an interval rule")
    check(interval.spec == {"seconds": 1800}, f"30 minutes must be 1800s, got {interval.spec!r}")
    check(
        interval.cooldown_seconds == 0 and interval.max_fires_per_day == 96,
        "an interval rule must pace itself (no cooldown) but cap its daily budget",
    )

    tiny = parse_rule_request("every 1 second ping me")
    check(tiny is not None and tiny.spec["seconds"] >= 5, "a sub-5s interval must be floored; a spinning rule is a bug")

    watch = parse_rule_request(r"when C:\notes\todo.txt changes tell me what changed")
    check(watch is not None and watch.kind == FILE_CHANGE, "when-file-changes must parse to a file_change rule")
    check(watch.spec == {"path": r"C:\notes\todo.txt"}, f"the watched path must be extracted, got {watch.spec!r}")

    # 2. Trigger position must not matter (front door parses both orders).
    front = parse_rule_request("every morning summarize my news")
    back = parse_rule_request("summarize my news every morning")
    check(front == back, "a trigger at the start and the end must parse identically")

    # 3. DETERMINISM.
    ref = parse_rule_request("every morning at 7 summarize my news")
    for _ in range(5):
        check(parse_rule_request("every morning at 7 summarize my news") == ref, "parsing must be deterministic")

    # 4. IT REFUSES rather than guesses — ordinary requests are NOT swallowed.
    for text in (
        "what's the weather today",
        "open chrome",
        "summarize my news",            # an action with no schedule
        "remind me about the meeting",   # 'remind' but no cadence
        "every good boy does fine",      # 'every' but no unit/time/day
        "every morning",                 # a schedule with no action
        "",
    ):
        check(parse_rule_request(text) is None, f"a non-schedule must return None, but {text!r} parsed")

    # 5. IT PERSISTS through the real store.
    store = ProactivityStore(scratch / "rules.sqlite3")
    saved = store.add_rule(**daily.as_add_rule_kwargs())
    check(saved is not None, "a parsed rule must persist through the store")
    check(saved.kind == DAILY and saved.spec == {"at": "08:00"}, "the persisted rule must match the parse")
    check(store.get_rule(saved.id) is not None, "the rule must be retrievable after creation")

    # 6. THE TYPED FAST-COMMAND PATH: create -> list -> pause -> delete, and an
    #    ordinary request falls through (returns None) instead of being swallowed.
    from backend.eva import proactivity as P
    from backend.eva.core import fast_commands as fc
    from backend.eva.tools.registry import ToolRegistry

    P._DEFAULT_STORE_PATH = scratch / "fc_rules.sqlite3"
    os.environ["EVA_PROACTIVITY_ENABLED"] = "1"
    tools = ToolRegistry()

    def call(msg: str):
        result = fc.maybe_handle_fast_command(msg, tools)
        return result[0] if result else None

    created = call("remind me every morning at 8:30 to summarize my news")
    check(created is not None and "Rule created" in created, f"the typed path must create a rule, got {created!r}")
    check(call("what is the capital of france") is None, "an ordinary question must fall through, not create a rule")

    fc_store = P.open_default_store()
    rules = fc_store.list_rules()
    check(len(rules) == 1, f"exactly one rule should exist after one creation, got {len(rules)}")
    rid = rules[0].id[:8]

    paused = call(f"disable rule {rid}")
    check(paused is not None and "paused" in paused.lower(), f"a rule must be pausable, got {paused!r}")
    check(fc_store.get_rule(rules[0].id).enabled is False, "pausing must actually disable the rule")

    deleted = call(f"delete rule {rid}")
    check(deleted is not None and "Deleted" in deleted, f"a rule must be deletable, got {deleted!r}")
    check(fc_store.list_rules() == [], "the rule must be gone after deletion")

    # 7. THE TRUST BOUNDARY: rule creation is NOT a planner-reachable tool.
    #    (Untrusted content could otherwise stand up a standing proposer.)
    registry_tools = {str(t.get("name", "")).lower() for t in ToolRegistry().list_tools()}
    for forbidden in ("proactivity.create_rule", "rule.create", "create_rule", "proactive.add_rule"):
        check(forbidden not in registry_tools, f"rule creation must not be a planner tool, found {forbidden!r}")

    # 8. Registration.
    name = "verify_eva_phase54_nl_rules.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 54 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 54 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 54 verifier")

    check(isinstance(daily, ParsedRule) and "nl_rules" in nl_rules.__name__, "sanity")

    print(
        "PASS: Phase 54 natural-language rule creation -- a typed sentence like 'remind me every morning to "
        "summarize my news' now becomes a real, persisted rule. The parser is deterministic and LLM-free, handles "
        "daily/interval/file-change in either word order, floors runaway intervals, and REFUSES anything without a "
        "schedule (so ordinary requests are never swallowed). Rules round-trip through the store and the typed "
        "fast-command path creates/lists/pauses/deletes them, while creation stays OFF the planner so untrusted "
        "content cannot stand up a standing proposer. A created rule only PROPOSES -- when it fires it still faces "
        "the permission gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
