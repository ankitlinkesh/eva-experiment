"""Typed-console learned-skills commands (Phase 47), split out of
``fast_commands.py`` in Phase 71 as a pure move -- no behavior changed.

A learned skill only ever COMPOSES existing gated tools -- it never writes
code -- and every proposal stays inert until explicitly approved; each step
of an approved skill still runs through the permission gate when executed.
"""
from __future__ import annotations

_SELF_IMPROVEMENT_DISABLED_MSG = (
    "Skill learning is off. Set EVA_SELF_IMPROVEMENT_ENABLED=1 to let me propose named skills from "
    "workflows that already worked. A skill only ever composes tools I already have — I never write code — "
    "and every proposal stays inert until you approve it."
)


def _open_skill_store():
    try:
        from ..self_improvement import open_default_store
        return open_default_store()
    except Exception:
        return None


def _learned_skills_list() -> str:
    store = _open_skill_store()
    if store is None:
        return _SELF_IMPROVEMENT_DISABLED_MSG
    skills = store.list_skills()
    if not skills:
        return "I haven't learned any skills yet. Say 'learn skills' and I'll look for workflows you repeat."
    lines = [f"Learned skills ({len(skills)}):"]
    for skill in skills[:15]:
        steps = " -> ".join(step.tool for step in skill.steps)
        lines.append(f"- [{skill.status}] {skill.name} (seen {skill.observed_count}x, used {skill.uses}x): {steps}")
    lines.append("Proposed skills are inert until you 'approve skill <name>'. Every step still runs through the gate.")
    return "\n".join(lines)


def _learn_skills_from_traces(tools: object) -> str:
    store = _open_skill_store()
    if store is None:
        return _SELF_IMPROVEMENT_DISABLED_MSG
    try:
        from ..self_improvement import learn_from_recent_traces
        result = learn_from_recent_traces(store, tools)
    except Exception:
        return "I couldn't read my traces to learn from just now."
    proposed = result.get("proposed") or []
    if not proposed:
        return (
            f"Looked at {result.get('scanned', 0)} trace(s) but found no workflow repeated often enough to name yet. "
            "(I only learn sequences that actually ran and worked, more than once.)"
        )
    lines = [f"From {result.get('scanned', 0)} trace(s) I propose {len(proposed)} skill(s):"]
    lines.extend(f"- {name}" for name in proposed)
    lines.append("These are inert until you approve them: 'approve skill <name>'.")
    return "\n".join(lines)


def _approve_learned_skill(identifier: str) -> str:
    store = _open_skill_store()
    if store is None:
        return _SELF_IMPROVEMENT_DISABLED_MSG
    skill = store.get_by_name(identifier.strip()) or store.get(identifier.strip())
    if skill is None:
        return f"I don't have a proposed skill called '{identifier}'."
    approved = store.approve(skill.id)
    if approved is None or not approved.is_runnable:
        return f"I couldn't approve '{identifier}'."
    steps = " -> ".join(step.tool for step in approved.steps)
    return f"Approved '{approved.name}': {steps}. It's runnable now — each step still goes through the gate."


def _run_learned_skill(name: str, tools: object) -> str:
    store = _open_skill_store()
    if store is None:
        return _SELF_IMPROVEMENT_DISABLED_MSG
    skill = store.get_by_name(name.strip())
    if skill is None:
        return f"I don't have a learned skill called '{name}'."
    try:
        from ..self_improvement import run_skill
        report = run_skill(skill, tools, store=store)
    except Exception:
        return f"I couldn't run '{name}' just now."
    if report.get("ok"):
        ran = ", ".join(step["tool"] for step in report.get("ran") or [])
        return f"Ran '{skill.name}': {ran}."
    reason = str(report.get("stopped_reason") or "")
    if reason.startswith("awaiting_confirmation:"):
        return (
            f"'{skill.name}' stopped at {report.get('gated_step')} — that step needs your confirmation, "
            "so I didn't run it or anything after it."
        )
    if reason.startswith("skill_not_approved:"):
        return f"'{skill.name}' is only proposed, not approved. Say 'approve skill {skill.name}' first."
    return f"'{skill.name}' stopped: {reason}"
