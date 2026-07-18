"""The encrypted vault (Phase 62-ish): saved personal info, DPAPI-encrypted at rest.

Lets a form be auto-filled from a value NOVA never shows the LLM and never
writes to disk in plaintext. Each value is individually encrypted with
Windows DPAPI (see :mod:`eva.vault.dpapi`) — bound to this Windows user
account, no passphrase, no unlock step.

Design choices that are load-bearing:

  * **Names, kinds, and labels are stored PLAINTEXT.** They are metadata, not
    secrets, and :meth:`Vault.list_entries` — the common operation, used to
    show "what do you have saved" — must work with *zero* decryption calls
    and zero secret plaintext ever entering process memory for that path.
  * **Per-entry ciphertext**, not one whole-file blob. A single corrupted or
    foreign (e.g. copied from another account) entry degrades to one
    unreadable field, not a dead vault.
  * **:class:`VaultEntry` carries no value.** This is structural, matching
    the discipline in :class:`eva.screen.form_filler.FillStep`: because the
    dataclass simply has no value field, no accidental ``asdict(entry)`` or
    logging call can ever serialize a secret. There is deliberately no
    ``show``/``dump``/``export``/``reveal`` method anywhere in this module —
    :meth:`Vault.resolve` is the *only* plaintext egress, and its only
    intended caller is a post-approval form handler.
"""

from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
import platform
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import dpapi

_VERSION = 1
_VALID_KINDS = {"identity", "login"}

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _machine_hint() -> str:
    """Advisory diagnostic only -- NEVER a security control.

    DPAPI itself is what makes a vault written on one Windows account unusable
    on another; this hint is only so a human/health-check can tell *why* an
    entry is failing to decrypt ("this vault looks like it came from a
    different account"), not something the code ever branches security on.
    """
    try:
        raw = f"{getpass.getuser()}|{platform.node()}".lower()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    except Exception:
        return ""


def _normalize_name(name: str) -> str:
    return str(name or "").strip().lower()


@dataclass(frozen=True)
class VaultEntry:
    """Metadata about a saved value. Deliberately has NO ``value`` field.

    ``has_ciphertext`` is a purely local, zero-decryption fact: does this
    entry carry a non-empty ciphertext string. It is NOT a claim that the
    ciphertext will actually decrypt on this machine/account -- e.g. a vault
    copied from another Windows account has a non-empty ciphertext on every
    entry, yet every one of them will fail to decrypt. That real check costs
    a DPAPI round trip per entry, so it deliberately lives in
    :meth:`Vault.health` (an explicit, rarely-called diagnostic) instead of
    here, where it would violate "listing never decrypts".
    """

    name: str
    kind: str
    label: str
    created_at: str
    updated_at: str
    has_ciphertext: bool = True


class Vault:
    """An encrypted, per-entry store of personal-info values.

    All public methods are wrapped to degrade (return False/None/empty)
    rather than raise, so a corrupt file or a DPAPI hiccup never breaks the
    chat path -- it just means that one thing couldn't be saved/read.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    # -- raw file I/O ---------------------------------------------------

    def _read_raw(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"version": _VERSION, "machine_hint": _machine_hint(), "entries": []}
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                return {"version": _VERSION, "machine_hint": _machine_hint(), "entries": []}
            data.setdefault("version", _VERSION)
            data.setdefault("machine_hint", _machine_hint())
            entries = data.get("entries")
            data["entries"] = entries if isinstance(entries, list) else []
            return data
        except Exception:
            # Corrupt/unreadable file: degrade to an empty vault rather than raising.
            return {"version": _VERSION, "machine_hint": _machine_hint(), "entries": []}

    def _write_raw(self, data: dict[str, Any]) -> bool:
        """Atomic write: write to a same-dir temp file, then os.replace."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(
                prefix=".vault-", suffix=".tmp", dir=str(self._path.parent)
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False)
                os.replace(tmp_name, self._path)
            finally:
                # If os.replace already succeeded the temp file no longer
                # exists at tmp_name; ignore a missing-file cleanup error.
                try:
                    if os.path.exists(tmp_name):
                        os.remove(tmp_name)
                except Exception:
                    pass
            return True
        except Exception:
            return False

    # -- public API -------------------------------------------------------

    def list_entries(self) -> list[VaultEntry]:
        """Metadata for every saved entry. Never decrypts, never touches values."""
        try:
            data = self._read_raw()
            out: list[VaultEntry] = []
            for raw in data.get("entries", []):
                if not isinstance(raw, dict):
                    continue
                try:
                    out.append(
                        VaultEntry(
                            name=str(raw.get("name", "")),
                            kind=str(raw.get("kind", "identity")),
                            label=str(raw.get("label", raw.get("name", ""))),
                            created_at=str(raw.get("created_at", "")),
                            updated_at=str(raw.get("updated_at", "")),
                            has_ciphertext=bool(raw.get("ciphertext")),
                        )
                    )
                except Exception:
                    continue
            return out
        except Exception:
            return []

    def has(self, name: str) -> bool:
        try:
            key = _normalize_name(name)
            return any(str(e.get("name")) == key for e in self._read_raw().get("entries", []))
        except Exception:
            return False

    def put(self, name: str, value: str, *, kind: str = "identity", label: str | None = None) -> bool:
        """Encrypt and store ``value``. Returns False and writes NOTHING on any failure.

        If DPAPI is unavailable this must never fall back to writing plaintext
        -- if it cannot be encrypted, it is simply not stored.
        """
        try:
            key = _normalize_name(name)
            if not key:
                return False
            if not dpapi.dpapi_available():
                return False
            ciphertext = dpapi.protect(str(value))
            if ciphertext is None:
                return False
            encoded = base64.b64encode(ciphertext).decode("ascii")
            display_kind = kind if kind in _VALID_KINDS else "identity"
            display_label = str(label).strip() if label else key

            with _lock:
                data = self._read_raw()
                entries = data.get("entries", [])
                now = _now_iso()
                existing = next((e for e in entries if str(e.get("name")) == key), None)
                if existing is not None:
                    existing["kind"] = display_kind
                    existing["label"] = display_label
                    existing["updated_at"] = now
                    existing["ciphertext"] = encoded
                else:
                    entries.append(
                        {
                            "name": key,
                            "kind": display_kind,
                            "label": display_label,
                            "created_at": now,
                            "updated_at": now,
                            "ciphertext": encoded,
                        }
                    )
                data["entries"] = entries
                data.setdefault("version", _VERSION)
                data.setdefault("machine_hint", _machine_hint())
                return self._write_raw(data)
        except Exception:
            return False

    def resolve(self, name: str) -> str | None:
        """The ONLY method that returns plaintext. None on any failure -- never raises.

        A foreign/corrupt ciphertext degrades to None for that one entry;
        other entries remain resolvable.
        """
        try:
            key = _normalize_name(name)
            data = self._read_raw()
            for raw in data.get("entries", []):
                if not isinstance(raw, dict) or str(raw.get("name")) != key:
                    continue
                encoded = raw.get("ciphertext")
                if not encoded:
                    return None
                try:
                    ciphertext = base64.b64decode(str(encoded))
                except Exception:
                    return None
                return dpapi.unprotect(ciphertext)
            return None
        except Exception:
            return None

    def delete(self, name: str) -> bool:
        try:
            key = _normalize_name(name)
            with _lock:
                data = self._read_raw()
                entries = data.get("entries", [])
                remaining = [e for e in entries if str(e.get("name")) != key]
                if len(remaining) == len(entries):
                    return False
                data["entries"] = remaining
                return self._write_raw(data)
        except Exception:
            return False

    def health(self) -> dict[str, Any]:
        """A real diagnostic. Unlike :meth:`list_entries`, this DOES decrypt.

        health() is explicit and rarely called (never on the hot chat path),
        so it can afford the one thing list_entries() cannot: actually try to
        decrypt every entry, so a vault that is silently 100% dead (e.g.
        copied to another machine, or the account's DPAPI key changed) is
        *diagnosable* instead of quietly reporting itself as fine. Every
        entry's ciphertext still decodes as bytes in that scenario -- only a
        real decrypt attempt reveals the failure.

        Never retains a decrypted value: each attempt is converted straight
        to a bool (name-and-outcome only) and the plaintext is dropped
        immediately, never logged, stored, or returned.
        """
        try:
            data = self._read_raw()
            raw_entries = [e for e in data.get("entries", []) if isinstance(e, dict)]
            total = len(raw_entries)
            undecryptable: list[str] = []

            for raw in raw_entries:
                name = str(raw.get("name", ""))
                encoded = raw.get("ciphertext")
                ok = False
                if encoded:
                    try:
                        ciphertext = base64.b64decode(str(encoded))
                        plaintext = dpapi.unprotect(ciphertext)
                        ok = plaintext is not None
                    except Exception:
                        ok = False
                    finally:
                        # Never keep the decrypted value around, even locally.
                        plaintext = None  # noqa: F841
                if not ok:
                    undecryptable.append(name)

            stored_hint = str(data.get("machine_hint", "") or "")
            current_hint = _machine_hint()
            # If the stored hint is missing (older/foreign file) we cannot
            # make a claim either way -- default to True so we don't invent
            # a false alarm out of an absent hint. This is advisory only, as
            # with machine_hint everywhere else: never a security control.
            written_by_this_account = (stored_hint == current_hint) if stored_hint else True

            fail_count = len(undecryptable)
            if total == 0:
                summary = "Vault is empty; nothing stored yet."
            elif fail_count == 0:
                summary = f"All {total} entries decrypt normally."
            elif not written_by_this_account:
                summary = (
                    f"{fail_count} of {total} entries cannot be decrypted; this vault appears to "
                    "have been written under a different Windows account."
                )
            else:
                summary = (
                    f"{fail_count} of {total} entries cannot be decrypted, even though this looks "
                    "like the same Windows account; the ciphertext may be corrupt."
                )

            return {
                "ok": True,
                "path": str(self._path),
                "dpapi_available": dpapi.dpapi_available(),
                "total_entries": total,
                "undecryptable_names": undecryptable,
                "written_by_this_account": written_by_this_account,
                "summary": summary,
            }
        except Exception:
            return {"ok": False, "path": str(self._path), "dpapi_available": dpapi.dpapi_available()}


__all__ = ["Vault", "VaultEntry"]
