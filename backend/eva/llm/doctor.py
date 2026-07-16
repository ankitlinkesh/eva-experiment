"""Provider health diagnostics — stop guessing which LLM actually works (Phase 48).

Eva has six configured providers, a key-rotation pool, and a per-purpose model
map. Any of it can rot silently: a key gets revoked, a model id is retired, a
provider order lists something with no key. When that happens nothing announces
it — calls just fall through the fallback chain and Eva quietly runs on whatever
still answers, or on nothing.

That is not hypothetical. Notes carried for weeks said "only Gemini works, NVIDIA
NIM has no key"; a live probe found the exact opposite — NIM was working and
primary, while two of six Gemini keys had been returning 404 for a retired model.
The beliefs were wrong in both directions because **there was no way to check**.

This module is the way to check.

  * :func:`configuration_report` is offline and CI-safe: it reports what is
    configured — which providers have keys, the provider order, how many
    rotation keys exist, which model each purpose maps to — and makes **no
    network calls whatsoever**. Safe to run anywhere, any time.
  * :func:`live_probe` actually calls each provider once. It is opt-in and never
    runs by default, because it costs real quota and real money.

Secrets never leave: only key *names*, presence, and lengths are ever reported —
never a value. Fail-safe throughout.
"""

from __future__ import annotations

import os
from typing import Any

# Every provider Eva knows, and the env var holding its key.
PROVIDER_KEY_ENV = {
    "nvidia_nim": "NVIDIA_NIM_API_KEY",
    "gemini": "GEMINI_API_KEY",  # plus the GEMINI_API_KEY_N rotation pool
    "openrouter": "OPENROUTER_API_KEY",
    "groq": "GROQ_API_KEY",
    "clod": "CLOD_API_KEY",
    "ollama": "",  # local, no key
}

_MAX_GEMINI_KEYS = 12


def gemini_key_names(environ: dict[str, str] | None = None) -> list[str]:
    """The names of every Gemini rotation key that is actually set."""
    env = environ if environ is not None else os.environ
    names: list[str] = []
    if str(env.get("GEMINI_API_KEY", "") or "").strip():
        names.append("GEMINI_API_KEY")
    for i in range(2, _MAX_GEMINI_KEYS + 1):
        name = f"GEMINI_API_KEY_{i}"
        if str(env.get(name, "") or "").strip():
            names.append(name)
    return names


def _has_key(name: str, environ: dict[str, str] | None = None) -> bool:
    if not name:
        return True  # ollama needs none
    env = environ if environ is not None else os.environ
    return bool(str(env.get(name, "") or "").strip())


def configuration_report(environ: dict[str, str] | None = None) -> dict[str, Any]:
    """What is configured, offline. NEVER makes a network call.

    Reports each provider's key presence, the effective provider order, and —
    the useful part — which providers appear in the order but have no key, i.e.
    every call wastes an attempt on them before reaching one that works.
    """
    env = environ if environ is not None else os.environ
    report: dict[str, Any] = {"providers": {}, "warnings": [], "network_used": False}

    try:
        for provider, key_env in PROVIDER_KEY_ENV.items():
            entry: dict[str, Any] = {"key_env": key_env or "(none needed)", "configured": _has_key(key_env, env)}
            if provider == "gemini":
                pool = gemini_key_names(env)
                entry["rotation_keys"] = pool
                entry["rotation_key_count"] = len(pool)
                entry["configured"] = bool(pool)
                entry["model"] = str(env.get("GEMINI_MODEL", "") or "")
            if provider == "nvidia_nim":
                entry["model"] = str(env.get("NVIDIA_NIM_MODEL", "") or "")
                entry["planner_model"] = str(env.get("NVIDIA_NIM_PLANNER_MODEL", "") or "")
                entry["deep_reasoning_model"] = str(env.get("NVIDIA_NIM_DEEP_REASONING_MODEL", "") or "")
            if provider == "openrouter":
                entry["model"] = str(env.get("OPENROUTER_MODEL", "") or "")
            if provider == "clod":
                entry["model"] = str(env.get("CLOD_MODEL", "") or "")
            report["providers"][provider] = entry

        raw_order = str(env.get("EVA_CLOUD_PROVIDER_ORDER", "") or "")
        order = [p.strip().lower() for p in raw_order.split(",") if p.strip()]
        report["provider_order"] = order

        # The actionable finding: a provider in the order with no key is a
        # guaranteed failed attempt on every single call.
        dead_in_order = [p for p in order if p in PROVIDER_KEY_ENV and not report["providers"][p]["configured"]]
        report["unconfigured_in_order"] = dead_in_order
        for provider in dead_in_order:
            report["warnings"].append(
                f"'{provider}' is in EVA_CLOUD_PROVIDER_ORDER but has no key — every call wastes an attempt on it."
            )
        if not any(report["providers"][p]["configured"] for p in order if p in PROVIDER_KEY_ENV):
            report["warnings"].append("No provider in the order has a key; Eva has no working cloud LLM.")
    except Exception as exc:  # pragma: no cover - defensive
        report["warnings"].append(f"diagnostic error: {str(exc)[:120]}")

    return report


def format_configuration_report(report: dict[str, Any]) -> str:
    """Human-readable configuration report (no secret values, ever)."""
    lines = ["LLM provider configuration (no network calls made):"]
    order = report.get("provider_order") or []
    lines.append(f"  order: {', '.join(order) if order else '(default)'}")
    for provider, entry in (report.get("providers") or {}).items():
        state = "configured" if entry.get("configured") else "NO KEY"
        extra = ""
        if entry.get("rotation_key_count"):
            extra += f", {entry['rotation_key_count']} rotation keys"
        if entry.get("model"):
            extra += f", model={entry['model']}"
        lines.append(f"  - {provider}: {state}{extra}")
    for warning in report.get("warnings") or []:
        lines.append(f"  ! {warning}")
    lines.append("  (Run a live probe to see which keys/models actually answer — that costs real quota.)")
    return "\n".join(lines)


async def live_probe(provider_names: list[str] | None = None, *, settings: Any = None) -> dict[str, Any]:
    """Actually call each provider once and report what answers.

    Opt-in and never run by default or in CI: this spends real quota. Returns
    per-provider ok/model/error. Never raises.
    """
    from .router import PROVIDER_CLASSES, LLMRateLimiter, _call_provider

    results: dict[str, Any] = {"network_used": True, "providers": {}}
    names = provider_names or [p for p in PROVIDER_KEY_ENV if p != "ollama"]
    messages = [{"role": "user", "content": "Reply with exactly: ok"}]
    limiter = LLMRateLimiter()

    for name in names:
        try:
            provider_cls = PROVIDER_CLASSES.get(name)
            if provider_cls is None:
                results["providers"][name] = {"ok": False, "error": "unknown provider"}
                continue
            provider = provider_cls(settings)
            response, _ = await _call_provider(provider, limiter, messages, purpose="chat", temperature=0.0, max_tokens=16)
            results["providers"][name] = {
                "ok": bool(getattr(response, "ok", False)),
                "model": str(getattr(response, "model", "")),
                "error": str(getattr(response, "error", "") or "")[:200],
            }
        except Exception as exc:
            results["providers"][name] = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:150]}"}
    return results


__all__ = [
    "configuration_report",
    "format_configuration_report",
    "live_probe",
    "gemini_key_names",
    "PROVIDER_KEY_ENV",
]
