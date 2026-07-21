"""Executable spec for vault decryption diagnostics (Phase 81).

An audit of the ~89 `except Exception: return None` sites found most to be
legitimate fail-safes (degrade-to-empty reads, fail-closed secret checks). One
was not: the vault's decryption path returned None for BOTH "no such secret" and
"the secret exists but did not decrypt" -- and the second case is, most often, a
value saved under a DIFFERENT Windows account, which DPAPI refuses. The form
filler then told the user "saved value not found" and sent them to re-save a
secret that was actually there. That is the wake-word bug class: a real failure
made indistinguishable from nothing-there.

The fix keeps every return contract ("None on failure", never raises) and only
records WHY on the side, so callers are untouched but a decrypt failure is now
diagnosable rather than silent.

Pinned here:
  1. resolve() distinguishes not_found from decrypt_failed, and still returns None.
  2. dpapi.unprotect records last_error and clears it on success.
  3. success carries no error.
"""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path

import pytest

from eva.vault import dpapi
from eva.vault.store import Vault


def _vault_with_entry(tmp: Path, name: str = "gmail", ciphertext: str = "AAAA") -> Vault:
    path = tmp / "vault.json"
    path.write_text(
        json.dumps({"version": 1, "machine_hint": "x", "entries": [{"name": name, "ciphertext": ciphertext, "domain": ""}]}),
        encoding="utf-8",
    )
    return Vault(path)


class TestResolveDistinguishesFailureModes:
    def test_absent_secret_is_not_found(self, tmp_path) -> None:
        vault = _vault_with_entry(tmp_path)
        assert vault.resolve("nonexistent") is None
        assert vault.last_resolve_error() == "not_found"

    def test_existing_but_undecryptable_is_not_reported_as_not_found(self, tmp_path, monkeypatch) -> None:
        """The whole point: an entry that is PRESENT but fails to decrypt must
        not read as absent."""
        vault = _vault_with_entry(tmp_path)
        monkeypatch.setattr(dpapi, "unprotect", lambda blob: None)
        monkeypatch.setattr(dpapi, "last_error", lambda: "decrypt_failed:winerr=13")
        assert vault.resolve("gmail") is None  # contract preserved
        assert vault.last_resolve_error() == "decrypt_failed:winerr=13"
        assert vault.last_resolve_error() != "not_found"

    def test_successful_resolve_carries_no_error(self, tmp_path, monkeypatch) -> None:
        vault = _vault_with_entry(tmp_path)
        monkeypatch.setattr(dpapi, "unprotect", lambda blob: "hunter2")
        assert vault.resolve("gmail") == "hunter2"
        assert vault.last_resolve_error() is None

    def test_bad_base64_is_decode_failed_not_not_found(self, tmp_path) -> None:
        vault = _vault_with_entry(tmp_path, ciphertext="a")  # invalid base64 padding
        assert vault.resolve("gmail") is None
        assert vault.last_resolve_error() == "decode_failed"

    def test_empty_ciphertext_is_empty_entry(self, tmp_path) -> None:
        vault = _vault_with_entry(tmp_path, ciphertext="")
        assert vault.resolve("gmail") is None
        assert vault.last_resolve_error() == "empty_entry"

    def test_resolve_never_raises(self, tmp_path, monkeypatch) -> None:
        vault = _vault_with_entry(tmp_path)

        def boom(blob):
            raise RuntimeError("kaboom")

        monkeypatch.setattr(dpapi, "unprotect", boom)
        # resolve wraps everything; must still return None, not propagate.
        assert vault.resolve("gmail") is None
        assert vault.last_resolve_error().startswith("exception:")


class TestDpapiLastError:
    def test_unavailable_records_reason(self, monkeypatch) -> None:
        monkeypatch.setattr(dpapi, "_LIBS", None)
        assert dpapi.unprotect(b"anything") is None
        assert dpapi.last_error() == "dpapi_unavailable"

    def test_empty_blob_records_reason(self, monkeypatch) -> None:
        # _LIBS may or may not be loaded; empty blob is checked either way.
        assert dpapi.unprotect(b"") is None
        assert dpapi.last_error() == "empty_blob"

    def test_success_clears_error(self, tmp_path) -> None:
        if not dpapi.dpapi_available():
            pytest.skip("DPAPI not available on this platform")
        blob = dpapi.protect("secret-value")
        assert blob is not None
        assert dpapi.unprotect(blob) == "secret-value"
        assert dpapi.last_error() is None
