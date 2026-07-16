"""Standalone verifier for Phase 48 (reasoning ceiling: provider diagnostics).

Phase 48's real finding was not a bug in the code — it was that nobody could
*tell* what was broken. Beliefs carried for weeks ("only Gemini works, NVIDIA NIM
has no key") turned out to be wrong in both directions the moment anything
actually probed: NIM was working and primary, while two of six Gemini keys had
been 404ing on a retired model id. So the deliverable is the instrument.

This verifies the instrument, offline:

  1. The configuration report is OFFLINE — proven by poisoning sockets, because
     a diagnostic that phones home would make CI slow, flaky, and expensive.
  2. It tells the truth about which providers have keys, and counts the Gemini
     rotation pool (skipping blank entries).
  3. THE ACTIONABLE FINDING: a provider listed in EVA_CLOUD_PROVIDER_ORDER with
     no key is flagged — that is a guaranteed failed attempt on every call.
  4. It never prints a secret VALUE, only names/presence.
  5. It is fail-safe on malformed configuration.
  6. The known-broken Clod model id is documented rather than replaced with an
     unverified guess (its real id could not be discovered: /models 403s and raw
     probes are Cloudflare-blocked).
  7. Registration in the master profiles.

No network, no live LLM, no env mutated.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def check(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> int:
    from backend.eva.llm.doctor import (
        PROVIDER_KEY_ENV,
        configuration_report,
        format_configuration_report,
        gemini_key_names,
    )
    from scripts import verify_eva_all

    # 1. Offline, proven by poisoning the network.
    report = configuration_report(environ={})
    check(report["network_used"] is False, "the configuration report must declare it made no network call")

    real_socket = socket.socket
    real_create = socket.create_connection

    def _boom(*args, **kwargs):
        raise AssertionError("the configuration report must never open a socket")

    try:
        socket.socket = _boom  # type: ignore[assignment]
        socket.create_connection = _boom  # type: ignore[assignment]
        poisoned = configuration_report(environ={"NVIDIA_NIM_API_KEY": "k"})
        check(poisoned["providers"]["nvidia_nim"]["configured"] is True, "the report must work with the network poisoned")
    finally:
        socket.socket = real_socket  # type: ignore[assignment]
        socket.create_connection = real_create  # type: ignore[assignment]

    # 2. Truthful key detection + rotation pool counting.
    env = {"NVIDIA_NIM_API_KEY": "k", "GEMINI_API_KEY": "a", "GEMINI_API_KEY_2": "b", "GEMINI_API_KEY_3": "   "}
    truthful = configuration_report(environ=env)
    check(truthful["providers"]["nvidia_nim"]["configured"] is True, "a provider with a key must read as configured")
    check(truthful["providers"]["groq"]["configured"] is False, "a provider with no key must read as unconfigured")
    check(gemini_key_names(environ=env) == ["GEMINI_API_KEY", "GEMINI_API_KEY_2"], "blank rotation keys must not be counted")
    check(truthful["providers"]["gemini"]["rotation_key_count"] == 2, "the gemini rotation pool must be counted")
    check(configuration_report(environ={})["providers"]["gemini"]["configured"] is False, "gemini with no keys must read unconfigured")

    # 3. THE ACTIONABLE FINDING: keyless providers in the order.
    wasteful = configuration_report(environ={"NVIDIA_NIM_API_KEY": "k", "EVA_CLOUD_PROVIDER_ORDER": "nvidia_nim,groq,clod"})
    check(set(wasteful["unconfigured_in_order"]) == {"groq", "clod"}, f"keyless providers in the order must be flagged, got {wasteful['unconfigured_in_order']!r}")
    check(any("wastes an attempt" in w for w in wasteful["warnings"]), "a keyless provider in the order must produce a warning")

    clean = configuration_report(environ={"NVIDIA_NIM_API_KEY": "k", "EVA_CLOUD_PROVIDER_ORDER": "nvidia_nim,ollama"})
    check(clean["unconfigured_in_order"] == [], "a clean order must produce no wasted-attempt finding")

    none_working = configuration_report(environ={"EVA_CLOUD_PROVIDER_ORDER": "gemini,openrouter"})
    check(any("no working cloud LLM" in w for w in none_working["warnings"]), "an order with no usable provider must warn loudly")

    # 4. Secrets never leak into the report.
    secret = "super-secret-key-value-123456"
    leaky = format_configuration_report(configuration_report(environ={"NVIDIA_NIM_API_KEY": secret, "GEMINI_API_KEY": secret}))
    check(secret not in leaky, "a diagnostic must NEVER print a key value")
    check("no network calls made" in leaky, "the report must state it is offline")

    # 5. Fail-safe on garbage.
    check(configuration_report(environ={"EVA_CLOUD_PROVIDER_ORDER": ",,,"})["provider_order"] == [], "a malformed order must degrade cleanly")
    for provider in ("nvidia_nim", "gemini", "openrouter", "groq", "clod", "ollama"):
        check(provider in PROVIDER_KEY_ENV, f"{provider} must be covered by the doctor")

    # 6. The known-broken Clod id is documented, not guessed.
    clod_source = (ROOT / "backend" / "eva" / "llm" / "providers" / "clod.py").read_text(encoding="utf-8")
    check("KNOWN BROKEN" in clod_source, "clod.py must document that its model id is known-broken rather than silently ship a guess")

    # 7. Registration.
    verifier_name = "verify_eva_phase48_reasoning.py"
    check(verifier_name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 48 verifier")
    check(verifier_name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 48 verifier")
    check(verifier_name in getattr(verify_eva_all, "VERIFIER_DESCRIPTORS"), "master verifier descriptor missing the Phase 48 verifier")

    print(
        "PASS: Phase 48 reasoning ceiling -- the provider doctor makes LLM rot visible instead of silent. The "
        "configuration report is provably offline (it still works with sockets poisoned) and never prints a key "
        "value, only names and presence; it truthfully reports which providers hold keys, counts the Gemini "
        "rotation pool while skipping blanks, and flags the actionable case -- a provider sitting in "
        "EVA_CLOUD_PROVIDER_ORDER with no key, which burns a guaranteed failed attempt on every call -- plus warns "
        "loudly when no provider in the order can work at all; it degrades cleanly on malformed config; and the "
        "known-broken Clod model id is documented as unverifiable rather than replaced with a guess."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
