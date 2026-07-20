"""Typed-console proactivity RULE-MUTATION commands (Phase 54), split out of
``fast_commands.py`` in Phase 71 as a pure move -- no behavior changed.

Only the create/delete/enable/disable commands live here. The read-only
status/report commands (``_proactivity_rules``, ``_proactivity_tick``,
``_proactivity_notifications``) stayed in ``fast_commands.py`` -- they weren't
part of this phase's scope and moving them added no clarity.

Trust boundary: rule creation is typed-console-ONLY, deliberately NOT a
planner tool, so untrusted content can't stand up a standing proposer. A
created rule only ever PROPOSES work -- every task it later queues still
faces the permission gate.
"""
from __future__ import annotations

from .fast_command_helpers import _PROACTIVITY_DISABLED_MSG


def _proactivity_create_rule(text: str) -> str | None:
    """Create a standing rule from a typed sentence (Phase 54).

    Returns ``None`` when the sentence has no recognisable schedule/trigger, so
    the dispatcher falls through to the normal path instead of the rule creator
    swallowing ordinary requests. A created rule only ever PROPOSES work — every
    task it later queues still faces the permission gate.
    """
    try:
        from ..proactivity import open_default_store, parse_rule_request, proactivity_enabled
    except Exception:
        return None
    parsed = parse_rule_request(text)
    if parsed is None:
        return None  # not a schedule we understand -> let other handlers try
    if not proactivity_enabled():
        return _PROACTIVITY_DISABLED_MSG
    # A rule's request text is persisted verbatim and later fed to the agent, so
    # it must not smuggle a live secret into storage or a future prompt.
    try:
        from ..privacy.secrets_broker import contains_secret_leak

        if contains_secret_leak(parsed.request):
            return "I won't put that in a saved rule — the request text looks like it contains a secret."
    except Exception:
        pass
    store = open_default_store()
    if store is None:
        return _PROACTIVITY_DISABLED_MSG
    rule = store.add_rule(**parsed.as_add_rule_kwargs())
    if rule is None:
        return "I understood the schedule but couldn't save that rule. Try rephrasing the action."
    return (
        f"Rule created: {parsed.summary}\n"
        f"It only proposes — when it fires it queues that request for approval and still runs through the gate. "
        f"Say 'rules' to see it, or 'delete rule {rule.id[:8]}' to remove it."
    )


def _proactivity_delete_rule(fragment: str) -> str:
    """Delete a rule by id or id-prefix (as shown by 'rules')."""
    try:
        from ..proactivity import open_default_store, proactivity_enabled
    except Exception:
        return "Proactivity is unavailable in this build."
    if not proactivity_enabled():
        return _PROACTIVITY_DISABLED_MSG
    store = open_default_store()
    if store is None:
        return _PROACTIVITY_DISABLED_MSG
    needle = fragment.strip().lower()
    matches = [r for r in store.list_rules() if r.id == needle or r.id.lower().startswith(needle)]
    if not matches:
        return f"No rule matches '{fragment}'. Say 'rules' to list them."
    if len(matches) > 1:
        ids = ", ".join(r.id[:8] for r in matches)
        return f"That prefix matches several rules ({ids}). Use more characters."
    target = matches[0]
    return f"Deleted rule: {target.name}" if store.delete_rule(target.id) else "Couldn't delete that rule."


def _proactivity_set_enabled(fragment: str, enabled: bool) -> str:
    """Pause ('disable') or resume ('enable') a rule by id-prefix."""
    try:
        from ..proactivity import open_default_store, proactivity_enabled
    except Exception:
        return "Proactivity is unavailable in this build."
    if not proactivity_enabled():
        return _PROACTIVITY_DISABLED_MSG
    store = open_default_store()
    if store is None:
        return _PROACTIVITY_DISABLED_MSG
    needle = fragment.strip().lower()
    matches = [r for r in store.list_rules() if r.id == needle or r.id.lower().startswith(needle)]
    if not matches:
        return f"No rule matches '{fragment}'. Say 'rules' to list them."
    if len(matches) > 1:
        ids = ", ".join(r.id[:8] for r in matches)
        return f"That prefix matches several rules ({ids}). Use more characters."
    updated = store.set_enabled(matches[0].id, enabled)
    if updated is None:
        return "Couldn't update that rule."
    return f"Rule {'enabled' if enabled else 'paused'}: {updated.name}"
