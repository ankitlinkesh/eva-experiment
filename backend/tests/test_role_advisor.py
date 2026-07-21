"""Executable spec for the delegation role advisor (Phase 79).

The advisor connects three things that never spoke: the agents/ specialists'
intent scoring, Phase 72's role policies, and the static skills catalog. Given a
goal with no role it recommends one and lists the skills that role can run.

The properties worth pinning:

  1. IT ADVISES, IT DOES NOT ACT. `delegate: <goal>` must never spawn a
     sub-task -- the person still picks the role and confirms. That is the
     Phase 73 trust boundary; a recommender that executed on its own guess would
     move the choice off the person and back within reach of untrusted content.
  2. A SUGGESTED SKILL IS ALWAYS RUNNABLE BY THE SUGGESTED ROLE. A skill is
     offered only if no tool it composes is RED under the role, so the advice is
     never a dead end.
  3. IT DECLINES RATHER THAN GUESSING. Below a confidence floor it says "pick
     one" instead of returning the alphabetically-first non-match.
  4. THE EXPLICIT PATH IS UNCHANGED. `delegate <role>: <goal>` still runs.
"""

from __future__ import annotations

from eva.agents.role_advisor import Advice, advise, score_roles, skills_for_role
from eva.agents.role_policy import RoleTier, known_roles, tier_for


class TestScoringPicksTheRightRole:
    def test_clear_goals_map_to_their_role(self) -> None:
        assert advise("summarize the codebase auth module").top == "code"
        assert advise("play some music").top == "media"
        assert advise("research the latest news on AI").top == "research"
        assert advise("click the login button and type text").top == "desktop"

    def test_below_confidence_it_declines(self) -> None:
        """A goal no specialist recognises yields no suggestion, not the
        alphabetically-first tie at the no-match floor."""
        result = advise("xyzzy plugh frobozz")
        assert result.top is None
        assert "Pick one explicitly" in result.as_text()

    def test_empty_goal_is_usage(self) -> None:
        assert "Usage: delegate:" in advise("").as_text()

    def test_ranking_is_complete_and_sorted(self) -> None:
        ranked = score_roles("play some music")
        assert {r.role for r in ranked} == set(known_roles())
        assert [r.score for r in ranked] == sorted((r.score for r in ranked), reverse=True)


class TestSuggestedSkillsAreAlwaysRunnable:
    def test_every_offered_skill_has_no_red_tool_under_its_role(self) -> None:
        for role in known_roles():
            for skill in skills_for_role(role):
                for tool in skill.allowed_tools:
                    assert tier_for(role, tool) is not RoleTier.RED, (
                        f"role {role} offered skill {skill.name} but is RED on {tool}"
                    )

    def test_role_specific_availability(self) -> None:
        """A web-search skill is research's, not media's; a screen skill is
        desktop's, not research's -- the filter really discriminates."""
        research_skills = {s.name for s in skills_for_role("research")}
        media_skills = {s.name for s in skills_for_role("media")}
        desktop_skills = {s.name for s in skills_for_role("desktop")}
        assert "search_web_and_remember_results" in research_skills
        assert "search_web_and_remember_results" not in media_skills
        assert "inspect_screen_once" in desktop_skills
        assert "inspect_screen_once" not in research_skills

    def test_advice_only_lists_runnable_skills(self) -> None:
        result = advise("research the latest news on AI")
        assert result.top == "research"
        assert set(result.skills) <= set(skills_for_role("research"))


class TestAdvisorAdvisesButNeverActs:
    def _handle(self, text, monkeypatch, spawned):
        import eva.core.fast_command_delegation as fcd

        def fake_run_delegated(role, goal, context):
            spawned.append((role, goal))
            raise AssertionError("advisor spawned a sub-task")

        monkeypatch.setattr(fcd, "run_delegated", fake_run_delegated)
        return fcd._handle_delegation_command(text.lower(), text, tools=None, session_context=None, memory=None, session_id=None)

    def test_delegate_colon_goal_never_spawns(self, monkeypatch) -> None:
        spawned: list = []
        out = self._handle("delegate: research the latest AI news", monkeypatch, spawned)
        assert out is not None
        assert spawned == []
        assert "delegate research:" in out[0]

    def test_delegate_goal_no_colon_advises(self, monkeypatch) -> None:
        spawned: list = []
        out = self._handle("delegate summarize the codebase", monkeypatch, spawned)
        assert out is not None and spawned == []
        assert "Suggested role: code" in out[0]

    def test_bare_delegate_lists_roles(self, monkeypatch) -> None:
        out = self._handle("delegate", monkeypatch, [])
        assert out is not None
        assert "Delegation roles" in out[0]


class TestExplicitPathStillRuns:
    def test_delegate_role_goal_calls_the_runner(self, monkeypatch) -> None:
        import eva.core.fast_command_delegation as fcd

        called: list = []

        class _Result:
            def as_text(self):
                return "ran"

        def fake_run_delegated(role, goal, context):
            called.append((role, goal))
            return _Result()

        monkeypatch.setattr(fcd, "run_delegated", fake_run_delegated)
        monkeypatch.setattr(fcd, "run_async", lambda coro: coro)
        out = fcd._handle_delegation_command(
            "delegate research: summarize x", "delegate research: summarize x",
            tools=None, session_context=None, memory=None, session_id=None,
        )
        assert called == [("research", "summarize x")]
        assert out == ("ran", "fast-command")
