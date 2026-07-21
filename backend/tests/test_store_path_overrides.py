"""Executable spec for env-overridable local-store paths (Phase 83).

Live feature testing found that the vault honoured ``EVA_VAULT_PATH`` but three
sibling local stores -- the learned-skill store, the proactivity rules store,
and the durable task queue -- hardcoded their paths. That is a testability gap
with teeth: probing the self-improvement store with a temp path silently wrote a
test skill into the REAL store, because ``open_default_store`` ignored the
override. Each now resolves an env override first, exactly like the vault, so a
test or a second profile cannot write into the real store.

Pinned: each ``default_*_path`` honours its override and falls back to the repo
default, and each ``open_default_*`` routes through it (so the instance really
uses the override, not just the pure function).
"""

from __future__ import annotations

from pathlib import Path

import pytest

CASES = [
    # module, path_fn, enable_flag, path_env, open_fn
    ("eva.self_improvement", "default_skills_path", "EVA_SELF_IMPROVEMENT_ENABLED", "EVA_SKILLS_PATH", "open_default_store"),
    ("eva.proactivity", "default_store_path", "EVA_PROACTIVITY_ENABLED", "EVA_PROACTIVITY_PATH", "open_default_store"),
    ("eva.tasks", "default_queue_path", "EVA_DURABLE_QUEUE_ENABLED", "EVA_TASKS_PATH", "open_default_queue"),
]


@pytest.mark.parametrize("module_name,path_fn,flag,path_env,open_fn", CASES)
def test_override_is_honoured_by_the_pure_path_function(module_name, path_fn, flag, path_env, open_fn, tmp_path):
    import importlib

    module = importlib.import_module(module_name)
    fn = getattr(module, path_fn)

    target = tmp_path / "override.sqlite3"
    assert fn({path_env: str(target)}) == target, f"{path_fn} ignored {path_env}"

    # No override -> the repo default (never the override).
    default = fn({})
    assert default != target
    assert str(default).endswith(".sqlite3") or str(default).endswith(".json")


@pytest.mark.parametrize("module_name,path_fn,flag,path_env,open_fn", CASES)
def test_open_default_routes_through_the_override(module_name, path_fn, flag, path_env, open_fn, tmp_path):
    import importlib

    module = importlib.import_module(module_name)
    opener = getattr(module, open_fn)

    target = tmp_path / "routed.sqlite3"
    env = {flag: "1", path_env: str(target)}
    instance = opener(env)
    assert instance is not None, f"{open_fn} returned None despite the flag being on"
    assert Path(instance.path) == target, f"{open_fn} did not use the {path_env} override (real store would be written)"


def test_disabled_still_returns_none_even_with_a_path_set(tmp_path):
    """The override must not accidentally enable a disabled feature."""
    import eva.self_improvement as si

    assert si.open_default_store({"EVA_SKILLS_PATH": str(tmp_path / "x.sqlite3")}) is None


def test_proactivity_engine_uses_the_override(tmp_path):
    import eva.proactivity as pro

    target = tmp_path / "engine_rules.sqlite3"
    engine = pro.open_default_engine({"EVA_PROACTIVITY_ENABLED": "1", "EVA_PROACTIVITY_PATH": str(target)})
    assert engine is not None
    assert Path(engine.store.path) == target


def test_matches_the_vault_pattern_it_was_modelled_on():
    """The vault already did this; the fix makes the siblings consistent."""
    from eva.vault import vault_path

    custom = "/tmp/eva_vault_probe.json"
    assert str(vault_path({"EVA_VAULT_PATH": custom})) == str(Path(custom))
