"""Standalone verifier for Phase 83 (env-overridable local-store paths).

Live feature testing (unlocking each flag one at a time) found the vault honoured
``EVA_VAULT_PATH`` but three sibling local stores hardcoded their paths: the
learned-skill store, the proactivity rules store, and the durable task queue.
The gap had teeth -- probing the self-improvement store with a temp path silently
wrote a test skill into the REAL store, because ``open_default_store`` ignored the
override entirely. Each now resolves an env override first, exactly like the
vault, so a test or a second profile cannot write into the real store.

What this verifies, for each of the three stores:
  1. The pure ``default_*_path`` function honours its env override.
  2. With no override it returns the repo default (never the override).
  3. ``open_default_*`` ROUTES THROUGH the override -- the opened instance's path
     is the override, so the fix reaches the real code path, not just the helper.
  4. A path override does not enable a disabled feature.
And a consistency check: the vault (the pattern these were modelled on) still
honours its own override.

Fully offline: opens sqlite stores under temp paths; the real stores are never
touched.
"""

from __future__ import annotations

import importlib
import sys
import tempfile
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


_CASES = [
    ("eva.self_improvement", "default_skills_path", "EVA_SELF_IMPROVEMENT_ENABLED", "EVA_SKILLS_PATH", "open_default_store"),
    ("eva.proactivity", "default_store_path", "EVA_PROACTIVITY_ENABLED", "EVA_PROACTIVITY_PATH", "open_default_store"),
    ("eva.tasks", "default_queue_path", "EVA_DURABLE_QUEUE_ENABLED", "EVA_TASKS_PATH", "open_default_queue"),
]


def main() -> int:
    tmp = Path(tempfile.mkdtemp())

    for module_name, path_fn, flag, path_env, open_fn in _CASES:
        module = importlib.import_module(module_name)
        resolve = getattr(module, path_fn)
        opener = getattr(module, open_fn)

        # 1 + 2: pure resolver
        target = tmp / f"{path_env}.sqlite3"
        check(resolve({path_env: str(target)}) == target, f"{path_fn} ignored {path_env}")
        default = resolve({})
        check(default != target, f"{path_fn} returned the override when none was set")

        # 3: opener routes through it -> the instance uses the override
        instance = opener({flag: "1", path_env: str(target)})
        check(instance is not None, f"{open_fn} returned None despite {flag}=1")
        check(
            Path(instance.path) == target,
            f"{open_fn} did not use the {path_env} override -- the real store would be written",
        )

        # 4: an override must not enable a disabled feature
        check(opener({path_env: str(target)}) is None, f"{open_fn} opened despite {flag} being unset")

    # Consistency: the vault is the pattern these were modelled on.
    from eva.vault import vault_path

    custom = str(tmp / "vault.json")
    check(str(vault_path({"EVA_VAULT_PATH": custom})) == custom, "the vault stopped honouring EVA_VAULT_PATH")

    # The proactivity engine (which wires store + queue) must honour it too.
    import eva.proactivity as pro

    engine = pro.open_default_engine({"EVA_PROACTIVITY_ENABLED": "1", "EVA_PROACTIVITY_PATH": str(tmp / "eng.sqlite3")})
    check(engine is not None and Path(engine.store.path) == tmp / "eng.sqlite3", "open_default_engine ignored the store override")

    import verify_eva_all

    name = "verify_eva_phase83_store_path_overrides.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 83 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 83 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 83 verifier")

    print(
        "PASS: Phase 83 env-overridable local-store paths. Live feature testing found the vault honoured EVA_VAULT_PATH "
        "but the learned-skill store, proactivity rules store, and durable task queue hardcoded theirs -- so probing "
        "the skill store with a temp path silently wrote into the REAL store. Each now resolves an env override first "
        "(EVA_SKILLS_PATH / EVA_PROACTIVITY_PATH / EVA_TASKS_PATH), exactly like the vault: the pure resolver honours "
        "the override and falls back to the repo default, open_default_* routes through it so the opened instance uses "
        "the override, and a path override never enables a disabled feature. The proactivity engine honours it too, and "
        "the vault it was modelled on still does."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
