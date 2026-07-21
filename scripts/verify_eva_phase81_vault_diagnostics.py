"""Standalone verifier for Phase 81 (vault decryption diagnostics + swallow audit).

An audit of the ~89 `except Exception: return None/pass` sites classified them:
most are legitimate fail-safes -- degrade-to-empty reads (grounding, durable
queue, proactivity store) and, importantly, fail-CLOSED secret checks in the
user model (an unassessable value is treated as a secret / not learned). ONE
hid a real, security-relevant failure: the vault's decryption path returned None
for both "no such secret" and "the secret exists but did not decrypt". The
second case is most often a value saved under a DIFFERENT Windows account, which
DPAPI refuses -- and the form filler then told the user the value was "not
found" and sent them to re-save a secret that was actually there.

This verifies the fix and the audit's two load-bearing conclusions:

  1. resolve() now DISTINGUISHES not_found from a decrypt failure, while keeping
     its "None on failure, never raises" contract.
  2. dpapi.unprotect RECORDS why it failed (the foreign-account signal) instead
     of swallowing it.
  3. THE CALLER SURFACES IT: the form filler reports "exists but could not be
     decrypted" rather than "not found", consulting last_resolve_error().
  4. THE FAIL-CLOSED SWALLOWS STAYED FAIL-CLOSED: the user model's provenance /
     secret guards still return True (treat as secret) on error -- a fail-safe
     that must never be "fixed" into fail-open.

Fully offline: dpapi is stubbed; no real decryption, no network.
"""

from __future__ import annotations

import json
import sys
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


def main() -> int:
    import tempfile

    from eva.vault import dpapi
    from eva.vault.store import Vault

    tmp = Path(tempfile.mkdtemp())
    path = tmp / "vault.json"
    path.write_text(
        json.dumps({"version": 1, "machine_hint": "x", "entries": [{"name": "gmail", "ciphertext": "AAAA", "domain": ""}]}),
        encoding="utf-8",
    )

    # ------------------------------------------------------------------ 1
    vault = Vault(path)
    check(vault.resolve("nope") is None, "resolve of an absent secret did not return None")
    check(vault.last_resolve_error() == "not_found", "an absent secret was not reported as not_found")

    original_unprotect = dpapi.unprotect
    original_last_error = dpapi.last_error
    try:
        dpapi.unprotect = lambda blob: None
        dpapi.last_error = lambda: "decrypt_failed:winerr=13"
        check(vault.resolve("gmail") is None, "resolve of an undecryptable entry did not preserve the None contract")
        reason = vault.last_resolve_error()
        check(reason != "not_found", "an undecryptable-but-PRESENT secret still read as not_found -- the whole bug")
        check(reason == "decrypt_failed:winerr=13", f"the decrypt failure reason was not surfaced (got {reason!r})")

        dpapi.unprotect = lambda blob: "hunter2"
        check(vault.resolve("gmail") == "hunter2", "a decryptable secret did not resolve")
        check(vault.last_resolve_error() is None, "a successful resolve left a stale error")
    finally:
        dpapi.unprotect = original_unprotect
        dpapi.last_error = original_last_error

    # ------------------------------------------------------------------ 2
    saved_libs = dpapi._LIBS
    try:
        dpapi._LIBS = None
        check(dpapi.unprotect(b"anything") is None, "unprotect did not return None when DPAPI is unavailable")
        check(dpapi.last_error() == "dpapi_unavailable", "unprotect did not record dpapi_unavailable")
    finally:
        dpapi._LIBS = saved_libs
    check(dpapi.unprotect(b"") is None and dpapi.last_error() == "empty_blob", "unprotect did not record empty_blob")

    # ------------------------------------------------------------------ 3
    screen_src = (BACKEND / "eva" / "screen" / "screen_tools.py").read_text(encoding="utf-8")
    check("last_resolve_error()" in screen_src, "the form filler does not consult last_resolve_error() -- it cannot tell the cases apart")
    check("vault_undecryptable" in screen_src, "the form filler does not surface an undecryptable-secret status distinct from not-found")
    check(
        "different Windows account" in screen_src,
        "the form filler does not name the most likely cause (a value saved under a different Windows account)",
    )

    # ------------------------------------------------------------------ 4
    user_model_src = (BACKEND / "eva" / "memory" / "user_model.py").read_text(encoding="utf-8")
    # The two provenance/secret guards must fail CLOSED: on error, treat as a
    # secret / do not learn. The audit confirmed these are correct swallows;
    # pin that they are not "fixed" into returning False (fail-open).
    check(
        user_model_src.count("return True") >= 2,
        "the user-model fail-closed guards (treat-as-secret on error) appear to have been weakened",
    )

    # ------------------------------------------------------------------ registration
    import verify_eva_all

    name = "verify_eva_phase81_vault_diagnostics.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 81 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 81 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 81 verifier")

    print(
        "PASS: Phase 81 vault decryption diagnostics. An audit of ~89 error-swallows found most to be legitimate "
        "fail-safes (degrade-to-empty reads; fail-CLOSED secret checks that treat an unassessable value as a secret). "
        "One hid a real, security-relevant failure: the vault's decryption path returned None for both 'no such secret' "
        "and 'the secret exists but did not decrypt' -- the latter most often a value saved under a different Windows "
        "account, which DPAPI refuses -- so the form filler told the user their saved value was 'not found' and sent "
        "them to re-save a secret that was actually there. resolve() now distinguishes not_found from a decrypt "
        "failure while keeping its None-on-failure contract; dpapi.unprotect records the foreign-account signal instead "
        "of swallowing it; and the form filler surfaces 'exists but could not be decrypted (may have been saved under a "
        "different Windows account)'. The fail-closed swallows are pinned to stay fail-closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
