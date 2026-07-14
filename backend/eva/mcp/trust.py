"""MCP trust model — only pinned servers, on a per-server budget (Phase 40c).

An MCP server is arbitrary third-party code whose tool *results* are untrusted
content (see taint tracking) and whose tools Eva can be asked to call. Two
controls keep that surface bounded:

  * a **trust allowlist** — a server's tools are only registered if the server
    is pinned as trusted (named in ``EVA_MCP_TRUSTED_SERVERS`` or marked
    ``"trusted": true`` in its config entry); and
  * a **per-server call budget** — each trusted server may be invoked at most
    ``EVA_MCP_SERVER_BUDGET`` times per process, so a compromised or runaway
    server cannot be called without bound.

Backward compatible: if no trust is configured at all (no env allowlist and no
server marks itself trusted), trust filtering is inert and every configured
server loads as before — the model activates the moment you pin anything.
MCP itself remains off unless ``EVA_MCP_ENABLED`` is set.
"""

from __future__ import annotations

import os
from threading import Lock

_DEFAULT_SERVER_BUDGET = 25

_call_counts: dict[str, int] = {}
_lock = Lock()


def trusted_allowlist() -> frozenset[str]:
    """Server names pinned as trusted via EVA_MCP_TRUSTED_SERVERS (comma/space sep)."""
    raw = os.environ.get("EVA_MCP_TRUSTED_SERVERS", "")
    names = [part.strip() for part in raw.replace(",", " ").split() if part.strip()]
    return frozenset(names)


def server_budget() -> int:
    """Max calls allowed per trusted MCP server per process."""
    raw = os.environ.get("EVA_MCP_SERVER_BUDGET", "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_SERVER_BUDGET
    return value if value >= 1 else _DEFAULT_SERVER_BUDGET


def trust_configured(servers: object = None) -> bool:
    """Whether any trust policy is in force (env allowlist or a marked server).

    When nothing is configured the model is inert (backward compatible) and
    every server is treated as trusted.
    """
    if trusted_allowlist():
        return True
    try:
        return any(bool(getattr(server, "trusted", False)) for server in (servers or ()))
    except TypeError:
        return False


def is_trusted(server: object, servers: object = None) -> bool:
    """Whether ``server`` is trusted under the current policy.

    Fail-safe: if trust is configured, a server must be explicitly pinned
    (named in the allowlist, or ``trusted`` on its config) to pass; otherwise
    (no policy configured) all servers are trusted for backward compatibility.
    """
    name = str(getattr(server, "name", "") or "")
    allow = trusted_allowlist()
    marked = bool(getattr(server, "trusted", False))
    if not trust_configured(servers if servers is not None else (server,)):
        return True
    if allow:
        return name in allow or marked
    return marked


def filter_trusted(servers: list) -> list:
    """Keep only the servers trusted under the current policy."""
    try:
        return [server for server in servers if is_trusted(server, servers)]
    except TypeError:
        return list(servers or [])


def record_call(server_name: str) -> int:
    """Count one call against a server's budget; returns the new total."""
    with _lock:
        total = _call_counts.get(server_name, 0) + 1
        _call_counts[server_name] = total
        return total


def budget_exceeded(server_name: str) -> bool:
    with _lock:
        return _call_counts.get(server_name, 0) >= server_budget()


def reset_budgets() -> None:
    """Clear per-server call counts (used by tests)."""
    with _lock:
        _call_counts.clear()
