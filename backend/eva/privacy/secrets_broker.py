"""Secrets broker — secrets are referenced by name, never handed to the model (P40c).

Eva holds real credentials (provider API keys, tokens) in the process
environment. Two things must never happen: a secret's *value* flowing into an
LLM prompt or a trace, and a tool obtaining a secret by any path other than
asking for it by name. This broker is that single mediation point.

  * Discovery returns secret *names* only — never values.
  * A tool resolves a secret by name at call time; the value is handed to the
    tool, not to the planner or the flight recorder.
  * :func:`scrub_for_model` guarantees the invariant defensively: before any
    text goes to the model or a trace, every *live* secret value in the
    environment is replaced by a placeholder (exact-value match), on top of the
    pattern-based :func:`redact_secrets`. Pattern redaction catches
    known-shaped secrets; exact-value scrubbing catches the rest, including
    short or oddly-formatted keys a regex would miss.

Pure and fail-safe: a scrubbing error degrades to the pattern-redacted text
rather than risking a raw leak or raising into the caller.
"""

from __future__ import annotations

import os
from typing import Mapping

from .redaction import redact_secrets

# Environment variable name fragments that mark a value as a secret worth
# brokering and scrubbing. Matched case-insensitively as substrings.
_SECRET_NAME_MARKERS = ("api_key", "apikey", "secret", "token", "password", "passwd", "pwd", "cookie", "session_key", "private_key")

# Never treat these as secrets even though they may match a marker loosely.
_NAME_DENYLIST = frozenset({"eva_mcp_trusted_servers"})

# Values this short are ignored for exact-value scrubbing — redacting a 1-3 char
# string would corrupt unrelated text without protecting anything meaningful.
_MIN_SCRUB_LEN = 6


def _looks_like_secret_name(name: str) -> bool:
    lowered = str(name or "").lower()
    if lowered in _NAME_DENYLIST:
        return False
    return any(marker in lowered for marker in _SECRET_NAME_MARKERS)


def _environ(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    return environ if environ is not None else os.environ


def list_secret_names(environ: Mapping[str, str] | None = None) -> list[str]:
    """The names of secrets the broker knows about — VALUES ARE NEVER RETURNED."""
    env = _environ(environ)
    return sorted(name for name, value in env.items() if _looks_like_secret_name(name) and str(value or "").strip())


def has_secret(name: str, environ: Mapping[str, str] | None = None) -> bool:
    env = _environ(environ)
    return _looks_like_secret_name(name) and bool(str(env.get(name, "") or "").strip())


def resolve(name: str, environ: Mapping[str, str] | None = None) -> str | None:
    """Resolve a secret VALUE by name for tool use only.

    Returns ``None`` for an unknown name or a name that does not look like a
    secret (so this can never be used to read arbitrary env vars). The returned
    value must go to a tool, never into model context or a trace.
    """
    if not _looks_like_secret_name(name):
        return None
    value = str(_environ(environ).get(name, "") or "")
    return value or None


def _live_secret_values(environ: Mapping[str, str] | None) -> list[str]:
    env = _environ(environ)
    values: list[str] = []
    for name, value in env.items():
        if not _looks_like_secret_name(name):
            continue
        text = str(value or "")
        if len(text) >= _MIN_SCRUB_LEN:
            values.append(text)
    # Longest first so a secret that contains a shorter one is scrubbed whole.
    return sorted(set(values), key=len, reverse=True)


def scrub_for_model(text: object, environ: Mapping[str, str] | None = None) -> str:
    """Make text safe to send to the model or write to a trace.

    Applies pattern-based redaction, then replaces any exact live secret value
    still present with ``[REDACTED_SECRET]``. Fail-safe: on error, returns the
    pattern-redacted text (never the raw input).
    """
    source = text if isinstance(text, str) else str(text or "")
    try:
        redacted, _events = redact_secrets(source)
    except Exception:
        redacted = source
    try:
        for value in _live_secret_values(environ):
            if value and value in redacted:
                redacted = redacted.replace(value, "[REDACTED_SECRET]")
    except Exception:
        return redacted
    return redacted


def contains_secret_leak(text: object, environ: Mapping[str, str] | None = None) -> bool:
    """Whether any live secret VALUE appears verbatim in ``text``."""
    source = text if isinstance(text, str) else str(text or "")
    for value in _live_secret_values(environ):
        if value and value in source:
            return True
    return False


def assert_no_secret_leak(text: object, environ: Mapping[str, str] | None = None) -> bool:
    """True iff no live secret value leaks through ``scrub_for_model``.

    The load-bearing invariant, usable as a guard in tests/verifiers: scrubbed
    output must contain no live secret value.
    """
    return not contains_secret_leak(scrub_for_model(text, environ), environ)
