"""Standalone verifier for Phase 79 (delegation role advisor).

Three things this project built to fit had never been wired together: the
agents/ specialists' intent scoring (``can_handle``, until now feeding only
status displays), Phase 72's role policies (the same five role names), and the
static skills catalog. The advisor joins them -- given a goal with no role it
recommends one and lists the skills that role can run -- and does so as an
ADVISOR only. This verifies the properties that make that safe and useful:

  1. IT ADVISES, IT NEVER ACTS. `delegate: <goal>` returns a recommendation and
     never spawns a sub-task, so the person still picks the role and confirms --
     the Phase 73 trust boundary. A recommender that executed on its guess would
     move that choice off the person and back within reach of untrusted content.
  2. A SUGGESTED SKILL IS ALWAYS RUNNABLE BY ITS ROLE. Skills are filtered by
     the SAME Phase 72 tiers, so a skill is offered only if no tool it composes
     is RED under the role -- the advice can never be a dead end.
  3. THE THREE SYSTEMS ARE ACTUALLY CONNECTED. Every role's scoring comes from a
     live specialist, and the filter really discriminates (a web skill is
     research's, a screen skill desktop's).
  4. IT DECLINES RATHER THAN GUESSING below a confidence floor.
  5. THE EXPLICIT PATH IS UNCHANGED: `delegate <role>: <goal>` still runs.

Fully offline: specialist string matching and set membership only. No LLM, no
gate, no sub-task ever runs.
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
    from eva.agents.role_advisor import advise, score_roles, skills_for_role
    from eva.agents.role_policy import RoleTier, known_roles, tier_for
    from eva.agents.registry import get_agent
    import eva.core.fast_command_delegation as fcd

    # ------------------------------------------------------------------ 3a
    # Every delegation role must be backed by a live specialist that scores.
    for role in known_roles():
        agent = get_agent(role)
        check(agent is not None, f"no specialist backs delegation role `{role}` -- scoring would be dead")

    # ------------------------------------------------------------------ 3b + 2
    for role in known_roles():
        for skill in skills_for_role(role):
            for tool in skill.allowed_tools:
                check(
                    tier_for(role, tool) is not RoleTier.RED,
                    f"role `{role}` was offered skill `{skill.name}` but is RED on `{tool}`",
                )

    research_skills = {s.name for s in skills_for_role("research")}
    media_skills = {s.name for s in skills_for_role("media")}
    desktop_skills = {s.name for s in skills_for_role("desktop")}
    check("search_web_and_remember_results" in research_skills, "research cannot run the web-search skill")
    check("search_web_and_remember_results" not in media_skills, "media was offered a web-search skill it is RED on")
    check("inspect_screen_once" in desktop_skills, "desktop cannot run the screen skill")
    check("inspect_screen_once" not in research_skills, "research was offered a screen skill it is RED on")

    # ------------------------------------------------------------------ scoring
    check(advise("summarize the codebase auth module").top == "code", "a code goal was not routed to code")
    check(advise("play some music").top == "media", "a media goal was not routed to media")
    check(advise("research the latest news on AI").top == "research", "a research goal was not routed to research")

    # ------------------------------------------------------------------ 4
    declined = advise("xyzzy plugh frobozz")
    check(declined.top is None, "the advisor guessed a role for a goal no specialist recognises")
    check("Pick one explicitly" in declined.as_text(), "the declining advice does not ask the user to pick")

    ranked = score_roles("play some music")
    check({r.role for r in ranked} == set(known_roles()), "scoring does not cover every role")

    # ------------------------------------------------------------------ 1
    spawned: list = []
    original_runner = fcd.run_delegated

    def _tripwire(role, goal, context):
        spawned.append((role, goal))
        raise AssertionError("the advisor spawned a sub-task")

    fcd.run_delegated = _tripwire
    try:
        advised = fcd._handle_delegation_command(
            "delegate: research the latest ai news", "delegate: research the latest ai news",
            tools=None, session_context=None, memory=None, session_id=None,
        )
        check(advised is not None, "the advisor did not handle `delegate: <goal>`")
        check(spawned == [], "the advisor spawned a sub-task instead of only advising")
        check("delegate research:" in advised[0], "the advice does not print the exact command to run")

        no_colon = fcd._handle_delegation_command(
            "delegate summarize the codebase", "delegate summarize the codebase",
            tools=None, session_context=None, memory=None, session_id=None,
        )
        check(no_colon is not None and spawned == [], "`delegate <goal>` (no colon) spawned or was unhandled")
        check("Suggested role: code" in no_colon[0], "`delegate <goal>` did not advise a role")
    finally:
        fcd.run_delegated = original_runner

    # ------------------------------------------------------------------ 5
    called: list = []

    class _Result:
        def as_text(self):
            return "ran"

    fcd.run_delegated = lambda role, goal, context: (called.append((role, goal)) or _Result())
    original_async = fcd.run_async
    fcd.run_async = lambda coro: coro
    try:
        out = fcd._handle_delegation_command(
            "delegate research: summarize x", "delegate research: summarize x",
            tools=None, session_context=None, memory=None, session_id=None,
        )
        check(called == [("research", "summarize x")], "the explicit `delegate <role>: <goal>` path no longer runs")
        check(out == ("ran", "fast-command"), "the explicit delegation return shape changed")
    finally:
        fcd.run_delegated = original_runner
        fcd.run_async = original_async

    # ------------------------------------------------------------------ 6
    import verify_eva_all

    name = "verify_eva_phase79_role_advisor.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 79 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 79 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 79 verifier")

    print(
        "PASS: Phase 79 delegation role advisor. Three pieces built to fit but never wired -- the agents/ specialists' "
        "intent scoring, Phase 72's role policies, and the static skills catalog -- are now one: `delegate: <goal>` "
        "recommends the best-fit role and lists the skills that role can run. It ADVISES ONLY and never spawns a "
        "sub-task, so the person still picks the role and confirms (the Phase 73 trust boundary). A skill is offered "
        "only if no tool it composes is RED under the role, filtered by the same Phase 72 tiers, so the advice is never "
        "a dead end; the filter really discriminates (a web skill is research's, a screen skill desktop's). Below a "
        "confidence floor it declines and asks the user to pick rather than returning the alphabetically-first "
        "non-match, and the explicit `delegate <role>: <goal>` path is unchanged."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
