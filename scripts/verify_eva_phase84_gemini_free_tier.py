"""Standalone verifier for Phase 84 (Gemini free-tier limits).

The router already rotated multiple Gemini API keys, but the rate limiter capped
gemini at a flat 4 RPM / 18 requests-per-DAY -- roughly 80x below Google's real
free tier. So the generous free quota was being thrown away by an
over-conservative soft limit, not by Google. (Live check this session: all four
configured keys answered gemini-2.5-flash in ~1s each; the keys were never the
problem.)

The fix gives gemini per-model limits like groq, applied per key:

  1. Each model gets a real free-tier RPD (2.5-flash 250, 2.0-flash 1500), not 18.
  2. The router's per-key ``model[keyN]`` slot suffix is stripped for the lookup,
     and each key slot is tracked independently -- so N keys give ~N x the daily
     quota, and exhausting one key does not block the next.
  3. Every value stays env-overridable (GEMINI_SOFT_RPM / GEMINI_SOFT_RPD).

Fully offline: no network, no key used; pure limit math and the local usage
counter.
"""

from __future__ import annotations

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


def main() -> int:
    import os

    from eva.llm.rate_limiter import GEMINI_MODEL_LIMITS, LLMRateLimiter, provider_limits

    # ------------------------------------------------------------------ 1
    check(provider_limits("gemini", "gemini-2.5-flash") == (10, 250), "gemini-2.5-flash is not at its real free-tier limit")
    check(provider_limits("gemini", "gemini-2.0-flash") == (15, 1500), "gemini-2.0-flash is not at its real free-tier limit")
    _, pro_rpd = provider_limits("gemini", "gemini-2.5-pro")
    _, flash_rpd = provider_limits("gemini", "gemini-2.5-flash")
    check(pro_rpd < flash_rpd, "pro is not tighter than flash")

    # The regression this exists to prevent: the flat 18/day cap.
    for model in GEMINI_MODEL_LIMITS:
        _, rpd = provider_limits("gemini", model)
        check(rpd >= 100, f"{model} is still throttled near the old 18/day cap ({rpd})")
    _, unknown_rpd = provider_limits("gemini", "gemini-9.9-experimental")
    check(unknown_rpd >= 100, "an unknown gemini model fell back to a throttled default")

    # ------------------------------------------------------------------ 2 (suffix)
    base = provider_limits("gemini", "gemini-2.0-flash")
    for slot in ("gemini-2.0-flash[key0]", "gemini-2.0-flash[key1]", "gemini-2.0-flash[key9]"):
        check(provider_limits("gemini", slot) == base, f"{slot} did not resolve to the base model limit")

    # ------------------------------------------------------------------ 2 (independence)
    os.environ["GEMINI_SOFT_RPD"] = "3"
    try:
        limiter = LLMRateLimiter(path=Path(tempfile.mkdtemp()) / "usage.json")
        for _ in range(3):
            ok, _r = limiter.can_call("gemini", "gemini-2.5-flash[key0]")
            check(ok, "key0 was blocked before reaching its own cap")
            limiter.record_success("gemini", "gemini-2.5-flash[key0]")
        ok0, reason0 = limiter.can_call("gemini", "gemini-2.5-flash[key0]")
        check(ok0 is False and reason0 == "soft_limit_exhausted:rpd", "key0 was not capped at its RPD")
        ok1, _r = limiter.can_call("gemini", "gemini-2.5-flash[key1]")
        check(ok1 is True, "exhausting key0 wrongly blocked key1 -- N keys would not multiply the quota")
    finally:
        os.environ.pop("GEMINI_SOFT_RPD", None)

    # ------------------------------------------------------------------ 3 (env override)
    os.environ["GEMINI_SOFT_RPD"] = "4242"
    os.environ["GEMINI_SOFT_RPM"] = "99"
    try:
        check(provider_limits("gemini", "gemini-2.5-flash") == (99, 4242), "GEMINI_SOFT_* env override was ignored")
    finally:
        os.environ.pop("GEMINI_SOFT_RPD", None)
        os.environ.pop("GEMINI_SOFT_RPM", None)

    # ------------------------------------------------------------------ registration
    import verify_eva_all

    name = "verify_eva_phase84_gemini_free_tier.py"
    check(name in verify_eva_all.FULL_VERIFIERS, "full profile missing the Phase 84 verifier")
    check(name in verify_eva_all.QUICK_VERIFIERS, "quick profile missing the Phase 84 verifier")
    check(name in verify_eva_all.VERIFIER_DESCRIPTORS, "master descriptor missing the Phase 84 verifier")

    print(
        "PASS: Phase 84 Gemini free-tier limits. The router already rotated multiple keys, but the rate limiter capped "
        "gemini at a flat 18 requests/DAY -- ~80x below Google's real free tier -- so the generous free quota was being "
        "thrown away by an over-conservative soft limit, not by Google (all four configured keys answered live this "
        "session). Gemini now has per-model limits like groq (2.5-flash 250/day, 2.0-flash 1500/day, pro tighter), the "
        "per-key model[keyN] slot suffix is stripped so each key gets the full per-model budget and is tracked "
        "independently (exhausting one key leaves the next free, so N keys give ~N x the quota -- 4 keys ~= 1000/day on "
        "2.5-flash or 6000/day on 2.0-flash), and every value stays env-overridable via GEMINI_SOFT_RPM/RPD."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
