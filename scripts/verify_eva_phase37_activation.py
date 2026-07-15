from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_DAILY_MIND_FLAGS = {
    "EVA_TRACING_ENABLED",
    "EVA_V2_VECTOR_MEMORY_ENABLED",
    "EVA_NATIVE_FUNCTION_CALLING",
    "EVA_USER_MODEL_ENABLED",  # Phase 43: durable user model (side-effect-free mind capability).
}


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.runtime.activation import (
        NEVER_AUTO_ENABLE,
        PROFILES,
        activate_profile,
        current_activation_status,
        profile_flags,
    )
    from backend.eva.core.fast_commands import maybe_handle_fast_command
    from backend.eva.tools.registry import ToolRegistry
    from scripts import verify_eva_all

    # Profiles exist and daily is exactly the side-effect-free mind flags.
    check("safe" in PROFILES and PROFILES["safe"] == {}, "safe profile must exist and be empty")
    check("daily" in PROFILES, "daily profile must exist")
    check(set(profile_flags("daily")) == _DAILY_MIND_FLAGS, "daily profile flags drifted from the mind set")

    # THE SAFETY INVARIANT: no profile may ever auto-enable a hands/external flag.
    for name in PROFILES:
        overlap = set(profile_flags(name)) & NEVER_AUTO_ENABLE
        check(not overlap, f"profile {name} auto-enables forbidden flags: {overlap}")

    # safe is a pure no-op; explicit settings are never overwritten.
    env: dict[str, str] = {}
    activate_profile("safe", environ=env)
    check(env == {}, "safe profile mutated the environment")

    env = {"EVA_TRACING_ENABLED": "0"}
    activate_profile("daily", environ=env)
    check(env["EVA_TRACING_ENABLED"] == "0", "activation overwrote an explicit operator setting")
    check(env.get("EVA_V2_VECTOR_MEMORY_ENABLED") == "1", "activation did not fill an unset mind flag")

    # startup wiring is present.
    main_source = (ROOT / "backend" / "eva" / "main.py").read_text(encoding="utf-8")
    check("_apply_activation_profile" in main_source, "main.py create_app does not apply the activation profile")

    # status is reported truthfully and the fast-command surfaces it.
    status = current_activation_status(environ={"EVA_PROFILE": "daily", "EVA_TRACING_ENABLED": "1"})
    check(status["mind"]["tracing"] is True, "status did not reflect an enabled mind flag")
    check(status["hands_external"]["real_input"] is False, "status wrongly reported real input on")

    result = maybe_handle_fast_command("activation status", ToolRegistry())
    check(result is not None, "activation status fast-command did not route")
    text = result[0].lower()
    check("activation profile" in text, "activation status report missing the profile line")
    check("never auto-enabled" in text or "manual only" in text, "activation report missing the safety boundary")

    # registered in the master verifier profiles.
    verifier_name = "verify_eva_phase37_activation.py"
    check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 37 activation verifier")
    descriptors = getattr(verify_eva_all, "VERIFIER_DESCRIPTORS")
    check(verifier_name in descriptors, "master verifier descriptor missing the Phase 37 activation verifier")

    print("PASS: Phase 37a activation profiles turn on only side-effect-free capabilities, never Eva's hands or external reach, and default to a byte-identical no-op.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
