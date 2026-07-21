"""Pure-ctypes bindings to Windows DPAPI (``crypt32.dll``).

DPAPI ties encryption to the *Windows user account*, not to a passphrase NOVA
would have to prompt for and hold in memory. There is no unlock step: any
process running as this Windows user can decrypt what this Windows user
encrypted, and nothing else can. That is the whole security model, and it is
also its whole limitation — it protects the vault file from being useful if
copied to another machine or opened under another account, not from another
program running as the *same* account.

No new dependency: this is plain ``ctypes`` against ``crypt32.dll`` /
``kernel32.dll``, not ``pywin32``'s ``win32crypt``, not ``cryptography``, not
``keyring``. On a non-Windows platform (or a Windows box missing the DLLs,
which should not happen but let's not crash the agent over it) the module
degrades to "DPAPI unavailable" rather than raising at import time.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

# Secondary entropy mixed into every DPAPI call. This is DEFENSE IN DEPTH
# ONLY, not a security boundary: it is a constant baked into source, so any
# code already running as this Windows user can read it and reproduce it. Its
# only effect is to stop a DIFFERENT DPAPI-using tool (or a raw copy/paste of
# a blob into some other app's "unprotect" call) from decrypting NOVA's vault
# by accident. It does not add a secret the attacker doesn't already have.
_ENTROPY = b"NOVA.vault.v1"

# Forbid any modal UI. Without this flag DPAPI is allowed to pop a Windows
# credential/consent dialog on certain failure paths (e.g. roaming profile
# issues). NOVA runs unattended/headless-adjacent; a blocking modal on a
# background agent thread would hang the process with no one to click it.
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _load() -> tuple[object, object] | None:
    """Load crypt32 + kernel32 and wire argtypes/restype. None on any failure."""
    try:
        crypt32 = ctypes.WinDLL("crypt32")
        kernel32 = ctypes.WinDLL("kernel32")

        crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),  # pDataIn
            wintypes.LPCWSTR,  # szDataDescr
            ctypes.POINTER(DATA_BLOB),  # pOptionalEntropy
            ctypes.c_void_p,  # pvReserved -- must be NULL
            ctypes.c_void_p,  # pPromptStruct
            wintypes.DWORD,  # dwFlags
            ctypes.POINTER(DATA_BLOB),  # pDataOut
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL

        crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(DATA_BLOB),  # pDataIn
            ctypes.c_void_p,  # ppszDataDescr -- out-param we don't want, pass None
            ctypes.POINTER(DATA_BLOB),  # pOptionalEntropy
            ctypes.c_void_p,  # pvReserved -- must be NULL
            ctypes.c_void_p,  # pPromptStruct
            wintypes.DWORD,  # dwFlags
            ctypes.POINTER(DATA_BLOB),  # pDataOut
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL

        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p

        return crypt32, kernel32
    except Exception:
        return None


_LIBS = _load()


def dpapi_available() -> bool:
    """Whether DPAPI bindings loaded successfully on this machine."""
    return _LIBS is not None


def _entropy_blob() -> DATA_BLOB:
    buf = ctypes.create_string_buffer(_ENTROPY, len(_ENTROPY))
    return DATA_BLOB(len(_ENTROPY), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _take_and_free(kernel32, blob: DATA_BLOB) -> bytes:
    """Copy bytes out of a LocalAlloc'd DPAPI output blob, then scrub+free it.

    Windows hands back ``pbData`` allocated via LocalAlloc; it is ours to
    free. We copy the bytes out FIRST (string_at makes an independent Python
    copy), then zero the original heap memory before freeing it so a
    decrypted secret does not linger, readable, in freed-but-not-yet-reused
    heap.
    """
    try:
        if not blob.pbData or blob.cbData <= 0:
            return b""
        data = ctypes.string_at(blob.pbData, blob.cbData)
        return data
    finally:
        if blob.pbData:
            try:
                ctypes.memset(blob.pbData, 0, blob.cbData)
            except Exception:
                pass
            try:
                kernel32.LocalFree(blob.pbData)
            except Exception:
                pass


def protect(plaintext: str) -> bytes | None:
    """Encrypt ``plaintext`` (UTF-8) with DPAPI. Never raises; None on failure."""
    if _LIBS is None:
        return None
    crypt32, kernel32 = _LIBS
    try:
        raw = plaintext.encode("utf-8")
        in_buf = ctypes.create_string_buffer(raw, len(raw))
        blob_in = DATA_BLOB(len(raw), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_char)))
        entropy = _entropy_blob()
        blob_out = DATA_BLOB()

        ok = crypt32.CryptProtectData(
            ctypes.byref(blob_in),
            None,  # szDataDescr
            ctypes.byref(entropy),
            None,  # pvReserved -- must be NULL
            None,  # pPromptStruct
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        )
        if not ok:
            return None
        return _take_and_free(kernel32, blob_out)
    except Exception:
        return None


# Why the last unprotect() failed, or None if it succeeded. The return contract
# stays "None on failure" so callers are untouched, but the REASON is recorded
# on the side (Phase 81). Without this, a decryption failure -- most importantly
# a blob encrypted under a DIFFERENT Windows account, which CryptUnprotectData
# rejects -- was indistinguishable from "no such secret", so a user on a second
# account was told their saved value did not exist and sent to re-save it.
_LAST_ERROR: str | None = None


def last_error() -> str | None:
    """Why the most recent unprotect() returned None (e.g. 'decrypt_failed:winerr=13',
    'dpapi_unavailable', 'empty_blob'), or None if it succeeded. Diagnostic only."""
    return _LAST_ERROR


def unprotect(blob: bytes) -> str | None:
    """Decrypt a DPAPI blob back to plaintext. Never raises; None on failure.

    Records why on failure in ``last_error()`` without changing the return.
    """
    global _LAST_ERROR
    if _LIBS is None:
        _LAST_ERROR = "dpapi_unavailable"
        return None
    if not blob:
        _LAST_ERROR = "empty_blob"
        return None
    crypt32, kernel32 = _LIBS
    try:
        in_buf = ctypes.create_string_buffer(bytes(blob), len(blob))
        blob_in = DATA_BLOB(len(blob), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_char)))
        entropy = _entropy_blob()
        blob_out = DATA_BLOB()

        ok = crypt32.CryptUnprotectData(
            ctypes.byref(blob_in),
            None,  # ppszDataDescr -- we don't want the description out-param
            ctypes.byref(entropy),
            None,  # pvReserved -- must be NULL
            None,  # pPromptStruct
            _CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(blob_out),
        )
        if not ok:
            # Capture the Windows error immediately -- a blob from another user
            # account fails here with a specific code rather than an exception.
            try:
                winerr = int(kernel32.GetLastError())
            except Exception:
                winerr = 0
            _LAST_ERROR = f"decrypt_failed:winerr={winerr}"
            return None
        raw = _take_and_free(kernel32, blob_out)
        result = raw.decode("utf-8")
        _LAST_ERROR = None
        return result
    except Exception as exc:
        _LAST_ERROR = f"exception:{type(exc).__name__}"
        return None


__all__ = ["dpapi_available", "protect", "unprotect", "last_error", "DATA_BLOB"]
