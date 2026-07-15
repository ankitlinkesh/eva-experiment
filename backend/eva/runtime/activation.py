"""Capability activation profiles — the safe "turn Eva on" switch (Phase 37).

Most of Eva's real capabilities are flag-gated OFF by default so the verifier
and test suites stay inert and nothing surprising happens on import. That is the
right default for CI, but it also means a real operator has to remember a
fistful of ``EVA_*`` env vars just to run Eva "for real". This module gives that
one switch: an ``EVA_PROFILE`` that turns on a coherent set of capabilities at
startup.

The safety line this module must never cross:

  * A profile may enable Eva's **mind** — self-observation (tracing), semantic
    memory, and native function-calling reasoning. These have no physical or
    external side-effect.
  * A profile may **never** auto-enable Eva's **hands or outward reach** — real
    mouse/keyboard input, a real browser, or external MCP servers. Those stay
    opt-in one flag at a time, so the permission gate remains the single
    authority for anything that touches the real world. ``NEVER_AUTO_ENABLE``
    encodes this and the Phase 37 verifier enforces it.

Two properties keep this from disturbing the existing safety model:

  * An explicit operator setting always wins — activation only ever fills in a
    flag the environment has left unset/empty; it never overwrites a value.
  * The default profile is ``safe`` (and any unknown name behaves like it),
    which sets nothing. Since the verifier/test suites never set ``EVA_PROFILE``,
    startup for them is byte-identical to before this module existed.
"""

from __future__ import annotations

import os
from typing import MutableMapping

# The daily-driver profile: side-effect-free "mind" capabilities only.
_DAILY_DRIVER_FLAGS: dict[str, str] = {
    "EVA_TRACING_ENABLED": "1",
    "EVA_V2_VECTOR_MEMORY_ENABLED": "1",
    "EVA_NATIVE_FUNCTION_CALLING": "1",
    "EVA_USER_MODEL_ENABLED": "1",
}

# Flags no profile may ever set automatically — Eva's hands and outward reach.
NEVER_AUTO_ENABLE: frozenset[str] = frozenset(
    {
        "EVA_ENABLE_REAL_INPUT",
        "EVA_V2_PLAYWRIGHT_ENABLED",
        "EVA_MCP_ENABLED",
    }
)

# Named profiles. "safe" is the current behavior (nothing auto-enabled).
PROFILES: dict[str, dict[str, str]] = {
    "safe": {},
    "daily": dict(_DAILY_DRIVER_FLAGS),
}

_TRUTHY_ABSENT = {"", "0", "false", "no", "off"}


def _normalize(profile: str | None) -> str:
    return (profile or "safe").strip().lower() or "safe"


def profile_flags(profile: str | None) -> dict[str, str]:
    """The flags a named profile would set (empty for safe/unknown names).

    Defensive: even if a profile dict ever listed a hands/external flag, it is
    filtered out here so the ``NEVER_AUTO_ENABLE`` guarantee cannot be bypassed
    by editing ``PROFILES`` alone.
    """
    flags = PROFILES.get(_normalize(profile), {})
    return {key: value for key, value in flags.items() if key not in NEVER_AUTO_ENABLE}


def activate_profile(
    profile: str | None = None,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, object]:
    """Apply an activation profile by setting only the flags left unset.

    ``profile`` defaults to ``EVA_PROFILE`` (or "safe"). Returns a summary of
    what changed. Never overwrites an explicit operator setting; never enables a
    ``NEVER_AUTO_ENABLE`` flag; the "safe"/unknown profile is a pure no-op.
    """
    env = environ if environ is not None else os.environ
    name = _normalize(profile if profile is not None else env.get("EVA_PROFILE"))
    flags = profile_flags(name)

    applied: dict[str, str] = {}
    already_set: dict[str, str] = {}
    for key, value in flags.items():
        current = env.get(key)
        if current is not None and current.strip() != "":
            already_set[key] = current
            continue
        env[key] = value
        applied[key] = value
    return {"profile": name, "applied": applied, "already_set": already_set}


def _is_on(env: MutableMapping[str, str], flag: str) -> bool:
    return env.get(flag, "").strip().lower() not in _TRUTHY_ABSENT


def current_activation_status(
    environ: MutableMapping[str, str] | None = None,
) -> dict[str, object]:
    """Report which capabilities are actually live right now, from real env state.

    Splits capabilities into ``mind`` (what a profile may enable) and
    ``hands_external`` (always manual/opt-in) so the report makes the safety
    boundary obvious.
    """
    env = environ if environ is not None else os.environ
    return {
        "profile": _normalize(env.get("EVA_PROFILE")),
        "mind": {
            "tracing": _is_on(env, "EVA_TRACING_ENABLED"),
            "vector_memory": _is_on(env, "EVA_V2_VECTOR_MEMORY_ENABLED"),
            "native_function_calling": _is_on(env, "EVA_NATIVE_FUNCTION_CALLING"),
            "user_model": _is_on(env, "EVA_USER_MODEL_ENABLED"),
        },
        "hands_external": {
            "real_input": _is_on(env, "EVA_ENABLE_REAL_INPUT"),
            "browser": _is_on(env, "EVA_V2_PLAYWRIGHT_ENABLED"),
            "mcp": _is_on(env, "EVA_MCP_ENABLED"),
        },
        "note": (
            "A profile may enable mind capabilities (tracing/memory/reasoning) but "
            "never hands or external reach (real input/browser/MCP); those stay opt-in "
            "one flag at a time, governed by the permission gate."
        ),
    }
