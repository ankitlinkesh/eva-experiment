"""The encrypted vault: DPAPI-backed personal info storage.

The safety property under test is not "encryption works" in the abstract --
it's narrower and more specific to how NOVA uses this: (1) listing what is
saved never needs to decrypt anything, (2) a value that cannot be encrypted
is never written as plaintext, (3) one corrupt/foreign entry never takes
down the rest of the vault, and (4) there is no method anywhere on Vault that
can dump a stored value except the one designated egress, ``resolve()``.

Every test uses ``tmp_path`` + the ``EVA_VAULT_PATH`` override so the real
vault on this machine is never touched.
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict
from pathlib import Path

import pytest

from eva.vault import Vault, VaultEntry, open_default_vault, vault_enabled, vault_path
from eva.vault import dpapi


def _skip_if_no_dpapi():
    if not dpapi.dpapi_available():
        pytest.skip("DPAPI unavailable on this platform")


# -- dpapi.py: raw ctypes bindings ------------------------------------------

def test_dpapi_roundtrip_and_ciphertext_hides_plaintext():
    _skip_if_no_dpapi()
    plaintext = "correct horse battery staple 42"
    blob = dpapi.protect(plaintext)
    assert blob is not None
    assert isinstance(blob, bytes)
    # The ciphertext must not contain the plaintext bytes anywhere in it.
    assert plaintext.encode("utf-8") not in blob

    recovered = dpapi.unprotect(blob)
    assert recovered == plaintext


def test_dpapi_unprotect_of_garbage_returns_none_not_raise():
    _skip_if_no_dpapi()
    assert dpapi.unprotect(b"not a real dpapi blob at all") is None


def test_dpapi_protect_never_raises_on_empty_string():
    _skip_if_no_dpapi()
    blob = dpapi.protect("")
    assert blob is not None
    assert dpapi.unprotect(blob) == ""


# -- VaultEntry: structurally value-free -------------------------------------

def test_vault_entry_has_no_value_field():
    entry = VaultEntry(
        name="email", kind="identity", label="Email",
        created_at="t0", updated_at="t0", has_ciphertext=True,
    )
    assert not hasattr(entry, "value")
    dumped = asdict(entry)
    assert "value" not in dumped
    # Nothing resembling a secret payload sneaks in via any field either.
    assert set(dumped.keys()) == {"name", "kind", "label", "created_at", "updated_at", "has_ciphertext"}


# -- flag off -----------------------------------------------------------------

def test_open_default_vault_is_none_when_flag_off(tmp_path):
    env = {"EVA_VAULT_ENABLED": "0", "EVA_VAULT_PATH": str(tmp_path / "vault.json")}
    assert vault_enabled(env) is False
    assert open_default_vault(env) is None


def test_open_default_vault_opens_when_flag_on(tmp_path, monkeypatch):
    monkeypatch.setenv("EVA_VAULT_ENABLED", "1")
    target = tmp_path / "sub" / "vault.json"
    monkeypatch.setenv("EVA_VAULT_PATH", str(target))
    assert vault_path() == target
    v = open_default_vault()
    assert isinstance(v, Vault)


# -- EVA_VAULT_PATH override ---------------------------------------------------

def test_vault_path_override_is_honored(tmp_path, monkeypatch):
    custom = tmp_path / "custom-dir" / "my-vault.json"
    monkeypatch.setenv("EVA_VAULT_PATH", str(custom))
    assert vault_path() == custom
    monkeypatch.delenv("EVA_VAULT_PATH", raising=False)
    assert vault_path() != custom


# -- list_entries(): plaintext metadata, decrypts nothing ---------------------

def test_list_entries_never_calls_unprotect(tmp_path, monkeypatch):
    _skip_if_no_dpapi()
    calls = {"n": 0}

    def counting_unprotect(blob):
        calls["n"] += 1
        return None

    monkeypatch.setattr(dpapi, "unprotect", counting_unprotect)

    vault = Vault(tmp_path / "vault.json")
    assert vault.put("email", "me@example.com", kind="identity", label="Email") is True
    assert vault.put("full_name", "Ada Lovelace", kind="identity", label="Full Name") is True

    entries = vault.list_entries()
    assert calls["n"] == 0, "list_entries() must never decrypt a value"
    names = {e.name for e in entries}
    assert names == {"email", "full_name"}
    assert all(e.has_ciphertext for e in entries)


def test_list_entries_marks_entry_without_ciphertext_without_decrypting(tmp_path, monkeypatch):
    _skip_if_no_dpapi()
    calls = {"n": 0}
    monkeypatch.setattr(dpapi, "unprotect", lambda blob: calls.__setitem__("n", calls["n"] + 1) or None)

    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)
    assert vault.put("email", "me@example.com") is True

    # Simulate a foreign/corrupt entry landing in the file directly (e.g. a
    # blob copied in from another account, or truncated by a bad write) --
    # ciphertext missing entirely.
    raw = json.loads(vault_file.read_text(encoding="utf-8"))
    raw["entries"].append(
        {
            "name": "broken",
            "kind": "identity",
            "label": "Broken",
            "created_at": "t0",
            "updated_at": "t0",
            "ciphertext": "",
        }
    )
    vault_file.write_text(json.dumps(raw), encoding="utf-8")

    entries = {e.name: e for e in vault.list_entries()}
    assert calls["n"] == 0, "list_entries() must never decrypt a value"
    assert entries["email"].has_ciphertext is True
    assert entries["broken"].has_ciphertext is False
    # NOTE: has_ciphertext only means "a ciphertext string is present" -- it
    # is not a claim that the ciphertext will actually decrypt (see the
    # health() tests below for the real, decrypting probe).


# -- put(): no plaintext fallback ----------------------------------------------

def test_put_returns_false_and_writes_nothing_when_dpapi_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(dpapi, "dpapi_available", lambda: False)
    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)

    ok = vault.put("email", "me@example.com")
    assert ok is False
    assert vault.list_entries() == []
    # Nothing at all should have been written for this entry.
    if vault_file.exists():
        assert "me@example.com" not in vault_file.read_text(encoding="utf-8")
        assert json.loads(vault_file.read_text(encoding="utf-8")).get("entries", []) == []


def test_put_when_dpapi_unavailable_never_writes_plaintext_value(tmp_path, monkeypatch):
    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)
    # Seed one real entry first so the file exists and has content.
    _skip_if_no_dpapi()
    assert vault.put("existing", "keepme") is True

    monkeypatch.setattr(dpapi, "dpapi_available", lambda: False)
    assert vault.put("secret_field", "TOP_SECRET_VALUE") is False
    contents = vault_file.read_text(encoding="utf-8")
    assert "TOP_SECRET_VALUE" not in contents
    assert vault.has("secret_field") is False
    # The pre-existing entry must be untouched.
    assert vault.has("existing") is True


# -- resolve(): the one plaintext egress, degrades on corruption --------------

def test_resolve_roundtrips_a_real_value(tmp_path):
    _skip_if_no_dpapi()
    vault = Vault(tmp_path / "vault.json")
    assert vault.put("email", "me@example.com", kind="identity", label="Email") is True
    assert vault.resolve("email") == "me@example.com"


def test_resolve_returns_none_for_missing_name(tmp_path):
    vault = Vault(tmp_path / "vault.json")
    assert vault.resolve("does_not_exist") is None


def test_corrupt_ciphertext_isolated_other_entries_still_resolve(tmp_path):
    _skip_if_no_dpapi()
    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)
    assert vault.put("email", "me@example.com") is True
    assert vault.put("phone", "555-0100") is True

    # Corrupt just the "email" ciphertext in place.
    raw = json.loads(vault_file.read_text(encoding="utf-8"))
    for entry in raw["entries"]:
        if entry["name"] == "email":
            entry["ciphertext"] = base64.b64encode(b"garbage-not-a-dpapi-blob").decode("ascii")
    vault_file.write_text(json.dumps(raw), encoding="utf-8")

    assert vault.resolve("email") is None
    assert vault.resolve("phone") == "555-0100"


def test_resolve_on_invalid_base64_returns_none_not_raise(tmp_path):
    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)
    raw = {
        "version": 1,
        "machine_hint": "",
        "entries": [
            {
                "name": "bad",
                "kind": "identity",
                "label": "Bad",
                "created_at": "t0",
                "updated_at": "t0",
                "ciphertext": "%%%not-base64%%%",
            }
        ],
    }
    vault_file.write_text(json.dumps(raw), encoding="utf-8")
    assert vault.resolve("bad") is None


# -- delete() ------------------------------------------------------------------

def test_delete_removes_entry(tmp_path):
    _skip_if_no_dpapi()
    vault = Vault(tmp_path / "vault.json")
    assert vault.put("email", "me@example.com") is True
    assert vault.delete("email") is True
    assert vault.has("email") is False
    assert vault.resolve("email") is None


def test_delete_missing_entry_returns_false(tmp_path):
    vault = Vault(tmp_path / "vault.json")
    assert vault.delete("nope") is False


# -- name normalization ---------------------------------------------------------

def test_name_normalization_email_equals_Email(tmp_path):
    _skip_if_no_dpapi()
    vault = Vault(tmp_path / "vault.json")
    assert vault.put("Email", "me@example.com") is True
    assert vault.has("email") is True
    assert vault.resolve("EMAIL") == "me@example.com"
    entries = vault.list_entries()
    assert len(entries) == 1
    assert entries[0].name == "email"

    # Putting under a different case updates the SAME entry, not a new one.
    assert vault.put("  EMAIL  ", "other@example.com") is True
    assert len(vault.list_entries()) == 1
    assert vault.resolve("email") == "other@example.com"


# -- no value-revealing API surface ---------------------------------------------

def test_no_show_dump_export_or_reveal_method_exists():
    forbidden_substrings = ("show", "dump", "export", "reveal")
    public_methods = [name for name in dir(Vault) if not name.startswith("_")]
    for name in public_methods:
        lowered = name.lower()
        for bad in forbidden_substrings:
            assert bad not in lowered, f"Vault.{name} looks like a plaintext-revealing method"


# -- health() -----------------------------------------------------------------
#
# Unlike list_entries(), health() is allowed to actually decrypt: it is an
# explicit, rarely-called diagnostic, not the hot path. That's the whole
# point -- it exists to catch the exact failure mode list_entries() can't
# see: a vault copied to another machine/account has non-empty ciphertext on
# every entry (has_ciphertext=True everywhere) yet nothing decrypts.

def test_health_reports_counts_and_dpapi_availability(tmp_path):
    _skip_if_no_dpapi()
    vault = Vault(tmp_path / "vault.json")
    vault.put("email", "me@example.com")
    h = vault.health()
    assert h["ok"] is True
    assert h["dpapi_available"] is True
    assert h["total_entries"] == 1
    assert h["undecryptable_names"] == []
    assert h["written_by_this_account"] is True
    assert "decrypt normally" in h["summary"]


def test_health_catches_every_entry_undecryptable_when_ciphertext_is_present_but_dead(tmp_path, monkeypatch):
    """The exact bug report: has_ciphertext=True everywhere, yet resolve() is
    dead for everything (e.g. vault copied to another Windows account). Only
    a real per-entry decrypt attempt in health() can see this -- confirm it
    does, and that it names EVERY entry, not just a subset."""
    _skip_if_no_dpapi()
    vault = Vault(tmp_path / "vault.json")
    assert vault.put("email", "me@example.com") is True
    assert vault.put("phone", "555-0100") is True
    assert vault.put("full_name", "Ada Lovelace") is True

    # list_entries() would still report has_ciphertext=True for all three --
    # simulate the "dead account" failure mode by making unprotect fail for
    # everyone, the same as it would after a SID change / different account.
    monkeypatch.setattr(dpapi, "unprotect", lambda blob: None)

    entries = vault.list_entries()
    assert all(e.has_ciphertext for e in entries), "sanity: ciphertext is still present on every entry"

    h = vault.health()
    assert h["total_entries"] == 3
    assert set(h["undecryptable_names"]) == {"email", "phone", "full_name"}
    assert "3 of 3" in h["summary"]


def test_health_never_retains_or_returns_a_plaintext_value(tmp_path):
    _skip_if_no_dpapi()
    vault = Vault(tmp_path / "vault.json")
    sentinel = "SENTINEL_PLAINTEXT_VALUE_MUST_NOT_LEAK_9f3a"
    assert vault.put("secret", sentinel) is True

    h = vault.health()
    blob = json.dumps(h, default=str)
    assert sentinel not in blob


def test_health_reports_mismatched_machine_hint_as_not_written_by_this_account(tmp_path):
    _skip_if_no_dpapi()
    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)
    assert vault.put("email", "me@example.com") is True

    # Simulate a vault copied in from a different Windows account: the
    # stored machine_hint no longer matches this account's hint, even though
    # (in this synthetic case) the ciphertext still happens to decrypt.
    raw = json.loads(vault_file.read_text(encoding="utf-8"))
    raw["machine_hint"] = "deadbeefdeadbeef"
    vault_file.write_text(json.dumps(raw), encoding="utf-8")

    h = vault.health()
    assert h["written_by_this_account"] is False


def test_health_undecryptable_and_mismatched_hint_gives_readable_summary(tmp_path, monkeypatch):
    _skip_if_no_dpapi()
    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)
    assert vault.put("email", "me@example.com") is True

    raw = json.loads(vault_file.read_text(encoding="utf-8"))
    raw["machine_hint"] = "deadbeefdeadbeef"
    vault_file.write_text(json.dumps(raw), encoding="utf-8")

    monkeypatch.setattr(dpapi, "unprotect", lambda blob: None)
    h = vault.health()
    assert h["undecryptable_names"] == ["email"]
    assert h["written_by_this_account"] is False
    assert "different Windows account" in h["summary"]


def test_health_isolates_one_bad_entry_from_the_rest(tmp_path):
    """One corrupt entry must not abort the whole health report."""
    _skip_if_no_dpapi()
    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)
    assert vault.put("email", "me@example.com") is True
    assert vault.put("phone", "555-0100") is True

    raw = json.loads(vault_file.read_text(encoding="utf-8"))
    for entry in raw["entries"]:
        if entry["name"] == "email":
            entry["ciphertext"] = "%%%not-base64%%%"
    vault_file.write_text(json.dumps(raw), encoding="utf-8")

    h = vault.health()
    assert h["ok"] is True
    assert h["total_entries"] == 2
    assert h["undecryptable_names"] == ["email"]


# -- on-disk format: plaintext metadata, opaque ciphertext ----------------------

def test_on_disk_file_never_contains_the_plaintext_value(tmp_path):
    _skip_if_no_dpapi()
    vault_file = tmp_path / "vault.json"
    vault = Vault(vault_file)
    secret_value = "hunter2-super-secret-password"
    assert vault.put("password", secret_value, kind="login", label="Password") is True

    contents = vault_file.read_text(encoding="utf-8")
    assert secret_value not in contents
    data = json.loads(contents)
    assert data["version"] == 1
    assert "machine_hint" in data
    entry = data["entries"][0]
    assert entry["name"] == "password"
    assert entry["kind"] == "login"
    assert entry["label"] == "Password"
    assert "ciphertext" in entry
    assert secret_value not in entry["ciphertext"]
