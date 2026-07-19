"""Pytest coverage for Phase 66: no registered tool may be stranded.

This is the pytest-visible companion to
``scripts/verify_eva_phase66_tool_reachability.py`` -- see that module's
docstring for the full invariant, method, and its documented limitations.
In short: every tool in ``ToolRegistry._tools`` must be reachable either
through ``planner_specs()`` (under the union of default and
``EVA_V2_PLAYWRIGHT_ENABLED=true``), or through an exact string-literal
reference in a production ``backend/eva/**/*.py`` module other than
``registry.py`` or ``roadmap/catalog.py`` (both excluded -- see below and
the verifier's docstring for why a declarative catalog OF tools cannot
prove anything routes to them).

REACHABLE MEANS ROUTED, NOT MERELY CALLABLE. Every registered tool is
already callable in principle through ``/api/tools/{tool_name}``, which
calls ``tools.run(tool_name, **body)`` for any name at all. That is exactly
how ``voice.listen_once`` and ``app.focus`` shipped stranded for phases --
both were callable in principle the whole time. This suite checks whether
something FIXED in the product chooses to call a tool for a real situation,
not whether a generic pass-through could reach it if asked.

HOW THIS DIFFERS FROM test_planner_reachability.py in this same directory:
that file asserts the opposite, security-facing direction -- that
``screen.*``/``web.*``/``mcp.*`` tools stay OUT of the planner by default
(and ``screen.*`` permanently, regardless of flags). This file asserts that
nothing REGISTERED is stranded from every production path -- a tool can
correctly stay planner-invisible forever (like ``screen.click``) while still
needing a production caller to pass here. Both are true at once and neither
subsumes the other; ``test_known_planner_only_and_source_only_tools_are_both_covered``
below exercises exactly that complementary relationship using
``screen.click`` as the concrete example.

THE PINNED FOUR: this verifier's first version excluded only ``registry.py``
and counted a ``roadmap/catalog.py`` entry as a valid reference. That masked
two genuinely stranded tools (``app.open``, ``file.patch_text``) behind
their own catalog entry, on top of the two it did catch
(``app.close_request``, ``file.read_text``) -- the exact laundering pattern
this phase exists to catch, in a new costume. ``test_catalog_py_exclusion_is_load_bearing``
below is a permanent regression test reproducing that defect directly: it
proves those two tools' ONLY non-registry reference lives inside
catalog.py, so excluding that one file is precisely what makes them
surface. The mutation tests further down are the ones that matter most
beyond that: they prove the detector actually fires (not just that it
happens to be quiet today).
"""

from __future__ import annotations

import pytest

from backend.eva.tools.registry import _MCP_TOOL_SPECS
from scripts import verify_eva_phase66_tool_reachability as phase66


@pytest.fixture(autouse=True)
def _clear_mcp_tool_specs_cache():
    """Same precaution as test_planner_reachability.py: don't let this
    file's registry constructions leak mcp.* specs into other test modules
    via the shared module-level cache, and don't inherit any left behind."""
    _MCP_TOOL_SPECS.clear()
    try:
        yield
    finally:
        _MCP_TOOL_SPECS.clear()


def _dummy_spec(name: str):
    from backend.eva.tools.registry import ToolSpec

    return ToolSpec(
        name=name,
        description="Test-only dummy tool: not planner-visible, not referenced anywhere in production source.",
        args_schema={"type": "object", "properties": {}, "required": []},
        safety_level="safe",
        handler=lambda **_kwargs: {"ok": True},
        action_type="SAFE_LOCAL_READ",
        risk_categories=("SAFE_LOCAL_READ",),
    )


# --- Ground truth, pinned. --------------------------------------------------

# The four true positives this phase found, and the working tool each one
# duplicates. Kept as one source of truth in this test file so every
# assertion below about them stays in sync.
_PINNED_COUNTERPARTS = {
    "app.close_request": "close_app",
    "app.open": "open_app",
    "file.patch_text": "file.write_text",
    "file.read_text": "workspace_read_file",
}


def test_expected_unreachable_is_pinned_to_the_four_found_duplicates():
    """As of Phase 66, exactly four registered tools have no product route:
    a shadow family of dotted tools duplicating a working, actually-routed
    alternative. If this ever needs a new entry, it must be added
    deliberately with a written reason -- not grown silently -- and if one
    of these four gets wired up or deleted, it must come back OUT."""
    assert set(phase66.EXPECTED_UNREACHABLE) == set(_PINNED_COUNTERPARTS)


def test_expected_unreachable_entries_are_true_positives_not_false_claims():
    """Each pinned entry must (a) name a real counterpart tool that IS
    itself reachable, and (b) say the tool is still callable via
    /api/tools rather than falsely claiming it cannot be called -- the
    coordinator caught this exact wording trap during review. app.open in
    particular must not be described as broken or dead: Phase 64 gave it a
    correct postcondition and it was live-verified opening a real app; it
    simply has no caller."""
    from backend.eva.tools.registry import ToolRegistry

    registry = ToolRegistry()
    reachable = set(registry._tools) - set(phase66.compute_unreachable(registry))

    for name, counterpart in _PINNED_COUNTERPARTS.items():
        reason = phase66.EXPECTED_UNREACHABLE[name]
        assert counterpart in reason, f"{name}'s justification must name its counterpart {counterpart!r}"
        assert counterpart in reachable, f"counterpart {counterpart!r} for {name} must itself be reachable"
        assert "cannot be called" not in reason.lower()
        assert "route" in reason.lower()

    # app.open's justification is allowed to SAY "not broken" (that is the
    # correct, reassuring claim); what it must never do is describe app.open
    # itself as broken/dead/unimplemented without immediately refuting it.
    # Check for the affirmative claim rather than bare word-absence, since
    # "it is correct, not broken" legitimately contains the word "broken".
    app_open_reason = phase66.EXPECTED_UNREACHABLE["app.open"].lower()
    assert "correct" in app_open_reason or "working" in app_open_reason or "live-verified" in app_open_reason
    assert "dead" not in app_open_reason
    assert "unimplemented" not in app_open_reason


def test_default_registry_unreachable_set_matches_the_pin_exactly():
    from backend.eva.tools.registry import ToolRegistry

    registry = ToolRegistry()
    unreachable = phase66.compute_unreachable(registry)
    assert set(unreachable) == set(phase66.EXPECTED_UNREACHABLE), (
        f"computed unreachable set drifted from the pin: {sorted(unreachable)}"
    )


def test_verifier_main_passes_against_the_real_registry():
    assert phase66.main() == 0


def test_catalog_py_exclusion_is_load_bearing():
    """Regression test for the exact defect the coordinator's review
    caught: counting roadmap/catalog.py as a production reference masks
    real stranded tools behind a purely declarative catalog entry.

    Directly reproduce it: app.open and file.patch_text's ONLY
    non-registry reference anywhere in backend/eva is inside catalog.py.
    With catalog.py wrongly counted (the pre-fix method -- only
    registry.py excluded), both look referenced. With catalog.py
    correctly excluded (the current method), neither does -- which is
    exactly why both now live in EXPECTED_UNREACHABLE instead of silently
    passing for the wrong reason."""
    from backend.eva.tools.registry import ToolRegistry

    catalog_names = phase66._string_constants(phase66.CATALOG_FILE)
    assert "app.open" in catalog_names
    assert "file.patch_text" in catalog_names

    # Pre-fix method: only registry.py excluded.
    referenced_without_catalog_exclusion: set[str] = set()
    for path in sorted(phase66.BACKEND_EVA.rglob("*.py")):
        if path.resolve() == phase66.REGISTRY_FILE:
            continue
        referenced_without_catalog_exclusion |= phase66._string_constants(path)
    assert "app.open" in referenced_without_catalog_exclusion, (
        "premise broken: app.open should look referenced when only registry.py is excluded"
    )
    assert "file.patch_text" in referenced_without_catalog_exclusion, (
        "premise broken: file.patch_text should look referenced when only registry.py is excluded"
    )

    # Current method: registry.py AND catalog.py excluded.
    referenced_with_catalog_excluded = phase66._production_referenced_names()
    assert "app.open" not in referenced_with_catalog_excluded
    assert "file.patch_text" not in referenced_with_catalog_excluded

    # And the live effect: both are genuinely unreachable against the real
    # registry today, matching the pin above.
    registry = ToolRegistry()
    unreachable = phase66.compute_unreachable(registry)
    assert "app.open" in unreachable
    assert "file.patch_text" in unreachable


# --- Complementary relationship with test_planner_reachability.py. ---------


def test_known_planner_only_and_source_only_tools_are_both_covered():
    from backend.eva.tools.registry import ToolRegistry

    registry = ToolRegistry()
    unreachable = phase66.compute_unreachable(registry)
    planner_names = {spec["name"] for spec in registry.planner_specs()}

    # "status" is reachable because it is directly planner-visible.
    assert "status" in planner_names
    assert "status" not in unreachable

    # "screen.click" must STAY planner-invisible (a permanent safety
    # boundary asserted by test_planner_reachability.py) yet still be
    # reachable here -- through eva/screen/form_filler.py's
    # run("screen.click", ...) and other production callers. This is the
    # concrete proof the two files are complementary, not duplicates.
    assert "screen.click" not in planner_names
    assert "screen.click" not in unreachable


def test_mcp_tools_absent_by_default_are_handled_honestly():
    """mcp.* tool names are built dynamically (f"mcp.{server.name}.{tool}")
    in eva/mcp/registration.py and are invisible to an exact-string scan by
    construction -- but they are also simply ABSENT from a default registry
    with no MCP server configured, so there is nothing to misclassify."""
    from backend.eva.tools.registry import ToolRegistry

    registry = ToolRegistry()
    assert not any(name.startswith("mcp.") for name in registry._tools)

    unreachable = phase66.compute_unreachable(registry)
    assert not any(name.startswith("mcp.") for name in unreachable)


# --- Mutation tests: the ones that prove the detector actually fires. ------


def test_mutation_a_an_unwired_registered_tool_is_caught_and_named():
    """Register a dummy tool that is neither planner-visible nor referenced
    by any production source. compute_unreachable() must report it, by
    name -- this is the exact shape of bug this phase exists to catch
    (voice.listen_once / app.focus, both shipped stranded for phases)."""
    from backend.eva.tools.registry import ToolRegistry

    registry = ToolRegistry()
    dummy_name = "zzz_test_stranded_dummy_tool"
    assert dummy_name not in registry._tools

    registry._tools[dummy_name] = _dummy_spec(dummy_name)
    try:
        unreachable = phase66.compute_unreachable(registry)
        assert dummy_name in unreachable, (
            f"a tool with no planner visibility and no production reference must be reported "
            f"unreachable; got {sorted(unreachable)}"
        )
    finally:
        del registry._tools[dummy_name]

    # Removing it restores exactly the pinned baseline (the four known
    # duplicates, no more) -- proves this is live detection against the
    # current registry state, not a stale fixture.
    clean = phase66.compute_unreachable(registry)
    assert dummy_name not in clean
    assert set(clean) == set(phase66.EXPECTED_UNREACHABLE)


def test_mutation_a_drives_a_real_verifier_failure_naming_the_tool(monkeypatch):
    """End-to-end version of mutation A: patch ToolRegistry so main() itself
    sees the stranded dummy tool, and confirm the verifier raises and names
    it. EXPECTED_TOOL_COUNT is bumped alongside the mutation so this test
    isolates the unreachable-set check specifically -- the separately
    pinned tool-count check is not the mechanism under test here, and
    letting it fire first would make this test pass for the wrong reason."""
    from backend.eva.tools import registry as registry_module

    dummy_name = "zzz_test_stranded_dummy_tool"
    real_init = registry_module.ToolRegistry.__init__

    def patched_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        self._tools[dummy_name] = _dummy_spec(dummy_name)

    monkeypatch.setattr(registry_module.ToolRegistry, "__init__", patched_init)
    monkeypatch.setattr(phase66, "EXPECTED_TOOL_COUNT", phase66.EXPECTED_TOOL_COUNT + 1)

    with pytest.raises(AssertionError) as excinfo:
        phase66.main()
    message = str(excinfo.value)
    assert dummy_name in message
    # The failure must be actionable: it should point at the three fixes.
    assert "wire it to a caller" in message.lower() or "wire it" in message.lower()


def test_mutation_b_a_wrongly_allowlisted_reachable_tool_fails_exact_match(monkeypatch):
    """Mutate EXPECTED_UNREACHABLE to falsely claim a genuinely reachable
    tool ("screen.click") is exempt. The exact-match comparison -- not a
    superset/subset check -- must catch this: an allowlist entry for a tool
    that is actually reachable is exactly how the list would rot into
    over-broad cover over time."""
    monkeypatch.setitem(
        phase66.EXPECTED_UNREACHABLE,
        "screen.click",
        "bogus entry injected by this test -- screen.click is genuinely reachable",
    )

    with pytest.raises(AssertionError) as excinfo:
        phase66.main()
    message = str(excinfo.value)
    assert "screen.click" in message
    assert "stale" in message.lower()
