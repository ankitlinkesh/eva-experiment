from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

STATE_PATH = Path(__file__).resolve().parents[1] / "data" / "llm_usage_state.json"
DEFAULT_RPM = {
    "gemini": 8,
    "groq": 20,
    "openrouter": 20,
    "clod": 10,
}
DEFAULT_RPD = {
    "gemini": 400,
    "groq": 1000,
    "openrouter": 50,
    "clod": 100,
}


def _now() -> int:
    return int(time.time())


def _minute_bucket() -> int:
    return _now() // 60


def _day_bucket() -> str:
    return time.strftime("%Y-%m-%d", time.localtime(_now()))


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _default_rpd(provider: str) -> int:
    if provider == "openrouter" and _env_bool("OPENROUTER_PAID_CREDITS"):
        return 1000
    if provider == "clod" and _env_bool("CLOD_HAS_CREDITS"):
        return 1000
    return DEFAULT_RPD.get(provider, 500)


def provider_limits(provider: str) -> tuple[int | None, int | None]:
    if provider == "ollama":
        return None, None
    prefix = provider.upper()
    rpm = _env_int(f"{prefix}_SOFT_RPM", DEFAULT_RPM.get(provider, 20))
    rpd = _env_int(f"{prefix}_SOFT_RPD", _default_rpd(provider))
    return rpm, rpd


class LLMRateLimiter:
    def __init__(self, path: Path = STATE_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def save(self, state: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")

    def _entry(self, state: dict[str, Any], provider: str) -> dict[str, Any]:
        entry = state.setdefault(provider, {})
        minute = _minute_bucket()
        day = _day_bucket()
        if entry.get("last_reset_minute") != minute:
            entry["last_reset_minute"] = minute
            entry["requests_this_minute"] = 0
        if entry.get("last_reset_day") != day:
            entry["last_reset_day"] = day
            entry["requests_today"] = 0
        entry.setdefault("blocked_until", 0)
        entry.setdefault("last_error", None)
        return entry

    def can_call(self, provider: str) -> tuple[bool, str | None]:
        if provider == "ollama":
            return True, None
        state = self.load()
        entry = self._entry(state, provider)
        rpm, rpd = provider_limits(provider)
        now = _now()
        if int(entry.get("blocked_until") or 0) > now:
            self.save(state)
            return False, f"blocked_until:{entry['blocked_until']}"
        if rpm is not None and int(entry.get("requests_this_minute") or 0) >= rpm:
            self.save(state)
            return False, "soft_rpm_exhausted"
        if rpd is not None and int(entry.get("requests_today") or 0) >= rpd:
            self.save(state)
            return False, "soft_rpd_exhausted"
        self.save(state)
        return True, None

    def record_success(self, provider: str) -> None:
        if provider == "ollama":
            return
        state = self.load()
        entry = self._entry(state, provider)
        entry["requests_this_minute"] = int(entry.get("requests_this_minute") or 0) + 1
        entry["requests_today"] = int(entry.get("requests_today") or 0) + 1
        entry["last_error"] = None
        self.save(state)

    def record_failure(self, provider: str, error: str, *, rate_limited: bool = False, retry_after_seconds: int | None = None) -> None:
        if provider == "ollama":
            return
        state = self.load()
        entry = self._entry(state, provider)
        entry["last_error"] = error[:500]
        if rate_limited:
            entry["blocked_until"] = _now() + int(retry_after_seconds or 60)
        self.save(state)

    def status(self) -> dict[str, Any]:
        state = self.load()
        for provider in list(state):
            self._entry(state, provider)
        self.save(state)
        return state
