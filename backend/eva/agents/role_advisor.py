"""Phase 79: a role advisor for delegation.

Three pieces of this project were built to fit and never wired together:

  * the ``agents/`` specialists' intent scoring (``can_handle``), which until
    now only fed status displays and drove nothing;
  * Phase 72's role policies -- the SAME five names (research/desktop/file/
    code/media), reached from the other side;
  * the static skills catalog (``agent/skills.py``), a set of tool compositions.

This module makes them one, as an ADVISOR and nothing more. Given a goal with
no role, it asks the specialists which role best fits, lists the skills that
role can actually run, and prints the exact ``delegate <role>: <goal>`` command
to run next. It never spawns a sub-task.

Why advice and not action: delegation is console-only precisely because whoever
picks the role and writes the goal decides where a sub-task goes, and that
choice must never be reachable from untrusted content (the Phase 73 boundary,
shared with rule creation in 54 and form filling in 58). A recommender that
executed on its own guess would move that decision off the person -- so this
recommends and stops. The specialists were already report-only; this keeps them
report-only and finally gives their scoring a consumer.

A skill is "available to a role" iff NONE of the tools it composes is RED under
that role's policy -- reusing Phase 72's tier exactly, so the advisor can never
suggest a skill the role would be refused mid-way. Pure and deterministic:
specialist string matching plus role_policy set membership. No LLM, no gate, no
execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..agent.skills import SKILLS, AgentSkill
from .role_policy import RoleTier, known_roles, tier_for

# The specialists return a low floor score (~0.04) for "I don't handle this" and
# a high score (~0.8-0.9) when a goal matches their keywords. A "top" at the
# floor is not a recommendation -- it is the alphabetically-first tie among
# non-matches -- so below this the advisor declines to suggest and asks the
# person to pick, rather than being confidently wrong.
_MIN_CONFIDENCE = 0.2


@dataclass(frozen=True)
class RoleScore:
    role: str
    score: float


def score_roles(goal: str) -> list[RoleScore]:
    """Score each delegation role against a goal, using its specialist's own
    ``can_handle``. Descending by score, then role name for a stable order.

    Fail-safe: a role whose specialist is missing or raises scores 0.0, so the
    advisor degrades to "no clear fit" rather than crashing.
    """
    from .registry import get_agent

    text = str(goal or "").strip()
    scores: list[RoleScore] = []
    for role in known_roles():
        score = 0.0
        if text:
            agent = get_agent(role)
            if agent is not None:
                try:
                    score = float(agent.can_handle(text))
                except Exception:
                    score = 0.0
        scores.append(RoleScore(role, score))
    scores.sort(key=lambda item: (-item.score, item.role))
    return scores


def skills_for_role(role: str) -> tuple[AgentSkill, ...]:
    """Static skills this role could run end to end -- every tool the skill
    composes is non-RED under the role's policy. A skill with even one RED tool
    is excluded, because the role would be refused partway and the advice would
    be a dead end."""
    runnable: list[AgentSkill] = []
    for skill in SKILLS:
        if all(tier_for(role, tool) is not RoleTier.RED for tool in skill.allowed_tools):
            runnable.append(skill)
    return tuple(runnable)


@dataclass(frozen=True)
class Advice:
    goal: str
    ranked: tuple[RoleScore, ...]
    top: str | None
    skills: tuple[AgentSkill, ...] = field(default_factory=tuple)

    def as_text(self) -> str:
        if not self.goal:
            return (
                "Usage: delegate: <goal>\n\n"
                f"I'll suggest which role fits. Or name one yourself: {', '.join(known_roles())}.\n"
                "Example: delegate: summarize this week's LLM pricing changes"
            )
        if self.top is None:
            return (
                f"No role clearly fits: \"{self.goal}\".\n"
                f"Pick one explicitly: {', '.join(known_roles())}.\n"
                f"Example: delegate {known_roles()[0]}: {self.goal}"
            )
        top_score = next((item.score for item in self.ranked if item.role == self.top), 0.0)
        others = ", ".join(f"{item.role} {item.score:.2f}" for item in self.ranked if item.role != self.top)
        lines = [f"Suggested role: {self.top} ({top_score:.2f})"]
        if others:
            lines.append(f"  {others}")
        if self.skills:
            lines.append(f"Skills {self.top} can run:")
            lines += [f"  - {skill.name}" for skill in self.skills]
        else:
            lines.append(f"({self.top} has no pre-built skills; it can still work the goal directly.)")
        lines.append(f"Run:  delegate {self.top}: {self.goal}")
        return "\n".join(lines)


def advise(goal: str) -> Advice:
    text = str(goal or "").strip()
    ranked = tuple(score_roles(text))
    top = ranked[0].role if ranked and ranked[0].score >= _MIN_CONFIDENCE else None
    skills = skills_for_role(top) if top is not None else ()
    return Advice(goal=text, ranked=ranked, top=top, skills=skills)


__all__ = ["RoleScore", "Advice", "score_roles", "skills_for_role", "advise"]
