"""Typed-console vault commands (Phase 62/67), split out of ``fast_commands.py``
in Phase 71 as a pure move -- no behavior changed.

Console-only by design, like the form-filling commands in ``fast_commands.py``:
NEVER a registry tool, NEVER a planner tool. The whole point of the vault is
that the model cannot reach it -- only a value-free ``@vault:name`` reference
can, and only through the gated ``screen.submit_form`` path. These handlers
never print a value: ``vault status``/``vault list`` show metadata only
(mirroring ``VaultEntry``'s deliberate lack of a value field), and
``save to vault`` echoes back only the name it stored.
"""
from __future__ import annotations

_VAULT_DISABLED_MSG = (
    "The vault is off. Set EVA_VAULT_ENABLED=1 to let me remember saved values "
    "(DPAPI-encrypted, tied to this Windows account) for form filling with @vault: references."
)


def _vault_status_command() -> str:
    try:
        from ..vault import open_default_vault, vault_enabled
    except Exception:
        return "The vault is unavailable in this build."
    if not vault_enabled():
        return _VAULT_DISABLED_MSG
    vault = open_default_vault()
    if vault is None:
        return _VAULT_DISABLED_MSG
    health = vault.health()
    if not health.get("ok"):
        return "Vault status check failed."
    lines = [
        f"Vault: {health.get('summary', '')}",
        f"Path: {health.get('path', '')}",
        f"DPAPI available: {health.get('dpapi_available')}",
        f"Written by this account: {health.get('written_by_this_account')}",
    ]
    undecryptable = health.get("undecryptable_names") or []
    if undecryptable:
        lines.append("Cannot decrypt: " + ", ".join(undecryptable))
    return "\n".join(lines)


def _vault_list_command() -> str:
    try:
        from ..vault import open_default_vault, vault_enabled
    except Exception:
        return "The vault is unavailable in this build."
    if not vault_enabled():
        return _VAULT_DISABLED_MSG
    vault = open_default_vault()
    if vault is None:
        return _VAULT_DISABLED_MSG
    entries = vault.list_entries()
    if not entries:
        return "Nothing saved in the vault yet. Say `save to vault <name> = <value>` to add one."
    lines = [f"Saved values ({len(entries)}):"]
    for entry in entries:
        binding = f" [bound to domain: {entry.domain}]" if entry.domain else ""
        lines.append(f"- {entry.name} ({entry.kind}) — {entry.label}{binding}")
    return "\n".join(lines)


_VAULT_KIND_HINTS = ("password", "pw", "login", "secret", "token")


def _vault_save_command(payload: str) -> str:
    """'save to vault <name> = <value>'. Echoes back only the NAME, never the
    value -- on any failure (e.g. DPAPI unavailable) says plainly that nothing
    was stored, rather than silently succeeding or leaking the value."""
    try:
        from ..vault import open_default_vault, vault_enabled
    except Exception:
        return "The vault is unavailable in this build."
    if not vault_enabled():
        return _VAULT_DISABLED_MSG
    if "=" not in payload:
        return "Usage: save to vault <name> = <value>"
    name, value = payload.split("=", 1)
    name = name.strip()
    value = value.strip()
    if not name or not value:
        return "Usage: save to vault <name> = <value>"
    lowered = name.lower()
    kind = "login" if any(hint in lowered for hint in _VAULT_KIND_HINTS) else "identity"
    vault = open_default_vault()
    if vault is None:
        return _VAULT_DISABLED_MSG
    if not vault.put(name, value, kind=kind):
        return f"Nothing was stored -- I couldn't encrypt '{name}' (DPAPI unavailable)."
    return f"Saved '{name}' to the vault."


def _vault_forget_command(name: str) -> str:
    try:
        from ..vault import open_default_vault, vault_enabled
    except Exception:
        return "The vault is unavailable in this build."
    if not vault_enabled():
        return _VAULT_DISABLED_MSG
    name = name.strip()
    if not name:
        return "Usage: forget vault <name>"
    vault = open_default_vault()
    if vault is None:
        return _VAULT_DISABLED_MSG
    return f"Deleted '{name}' from the vault." if vault.delete(name) else f"No saved value named '{name}'."


def _vault_bind_command(payload: str) -> str:
    """'bind vault <name> to domain <domain>' (Phase 67) -- declare that
    ``@vault:<name>`` only fills on pages whose browser-reported origin
    matches ``<domain>``. Metadata-only: never touches the encrypted value,
    and a SEPARATE command from `save to vault` on purpose, so a domain
    string can never collide with (or be mistaken for) part of a saved
    value's own text.
    """
    try:
        from ..vault import open_default_vault, vault_enabled
    except Exception:
        return "The vault is unavailable in this build."
    if not vault_enabled():
        return _VAULT_DISABLED_MSG
    if " to domain " not in payload.lower():
        return "Usage: bind vault <name> to domain <domain>  (e.g. bind vault work_login to domain mybank.com)"
    idx = payload.lower().index(" to domain ")
    name = payload[:idx].strip()
    domain = payload[idx + len(" to domain "):].strip()
    if not name or not domain:
        return "Usage: bind vault <name> to domain <domain>  (e.g. bind vault work_login to domain mybank.com)"
    vault = open_default_vault()
    if vault is None:
        return _VAULT_DISABLED_MSG
    if not vault.has(name):
        return f"No saved value named '{name}'. Say `vault list` to see what's saved."
    if not vault.set_domain(name, domain):
        return f"Could not bind '{name}' to a domain."
    return f"'{name}' will now only fill on pages whose address bar shows '{domain}'."


def _vault_unbind_command(name: str) -> str:
    """'unbind vault <name>' (Phase 67) -- clear a previously declared domain
    binding, returning the entry to its default (fills on any page)."""
    try:
        from ..vault import open_default_vault, vault_enabled
    except Exception:
        return "The vault is unavailable in this build."
    if not vault_enabled():
        return _VAULT_DISABLED_MSG
    name = name.strip()
    if not name:
        return "Usage: unbind vault <name>"
    vault = open_default_vault()
    if vault is None:
        return _VAULT_DISABLED_MSG
    if not vault.has(name):
        return f"No saved value named '{name}'."
    vault.set_domain(name, "")
    return f"'{name}' is no longer bound to a domain."
